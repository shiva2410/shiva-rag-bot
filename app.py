import json
import os
from pathlib import Path

from fastapi import FastAPI, Request
from pydantic import BaseModel
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from data.portfolio_data import PORTFOLIO


BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="Shiva Thavani | AI Engineer",
    description="Machine Learning Engineer specializing in GenAI, Agentic AI, LLMOps, and enterprise AI systems.",
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


class AskRequest(BaseModel):
    question: str


def answer_question(question: str) -> dict:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return {
            "answer": "Gemini is ready, but the API key is not configured yet.",
            "bullets": [
                "Set `GEMINI_API_KEY` in your local terminal or PythonAnywhere environment.",
                "Restart the web app after setting the key.",
                "The assistant will then answer from Shiva's expanded knowledge base using Gemini.",
            ],
        }

    try:
        from google import genai
        from google.genai import types
        from google.genai.errors import APIError
    except ImportError:
        return {
            "answer": "Gemini support is configured, but the `google-genai` package is not installed.",
            "bullets": [
                "Run `pip install -r requirements.txt`.",
                "Restart the FastAPI server after installation.",
            ],
        }

    knowledge = (BASE_DIR / "data" / "shiva_knowledge_base.txt").read_text(encoding="utf-8")
    prompt = f"""
You are Shiva Thavani's AI portfolio assistant.

Use only the knowledge base below to answer. Do not mention sources, citations,
the knowledge base, hidden context, or documents. If the answer is not covered,
say that you do not have enough information in Shiva's profile.

Return valid JSON only with this exact shape:
{{
  "answer": "one concise sentence",
  "bullets": ["3 to 5 short, high-signal bullet points"]
}}

Style rules:
- Be concise and recruiter-friendly.
- No long paragraphs.
- Prefer metrics, systems, tools, and impact.
- Use first person only if the question directly asks as Shiva; otherwise use "Shiva".

Question:
{question}

Knowledge base:
{knowledge}
"""
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.35,
                response_mime_type="application/json",
            ),
        )
    except APIError:
        return {
            "answer": "Gemini could not generate an answer right now.",
            "bullets": [
                "Check that `GEMINI_API_KEY` is valid.",
                "Confirm the PythonAnywhere web app has internet access for API calls.",
                "Restart the web app after changing environment variables.",
            ],
        }
    except Exception:
        return {
            "answer": "The assistant hit an unexpected Gemini configuration issue.",
            "bullets": [
                "Verify `GEMINI_API_KEY` is set.",
                "Verify `GEMINI_MODEL` is set to a valid model, or leave it unset to use `gemini-2.5-flash`.",
            ],
        }
    try:
        parsed = json.loads(response.text or "{}")
    except json.JSONDecodeError:
        parsed = {"answer": response.text or "I could not generate a clean answer.", "bullets": []}

    return {
        "answer": str(parsed.get("answer", "")).strip() or "I do not have enough information in Shiva's profile.",
        "bullets": [str(item).strip() for item in parsed.get("bullets", []) if str(item).strip()][:5],
    }


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "portfolio": PORTFOLIO,
            "seo": PORTFOLIO["seo"],
        },
    )


@app.get("/resume")
async def resume():
    return FileResponse(
        BASE_DIR / "static" / "resume" / "Shiva_Resume.pdf",
        media_type="application/pdf",
        filename="Shiva_Resume.pdf",
    )


@app.get("/health")
async def health():
    return {"status": "ok", "service": "portfolio"}


@app.post("/api/ask")
async def ask_resume(payload: AskRequest):
    question = payload.question.strip()
    if not question:
        return {
            "answer": "Ask me about Shiva's experience, GenAI work, MLOps platforms, hackathons, skills, or education.",
            "bullets": [
                "Try one of the quick prompts under the search bar.",
                "Gemini answers from Shiva's expanded portfolio knowledge base.",
            ],
        }
    return answer_question(question)
