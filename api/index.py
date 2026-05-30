import os
import sys
import json
import asyncio
from pathlib import Path
from functools import lru_cache
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from mangum import Mangum

# ---------------------------------------------------------------------------
# Load .env for local development (no-op on Vercel where env vars are injected
# directly into the process environment at runtime).
# ---------------------------------------------------------------------------
load_dotenv()

# ---------------------------------------------------------------------------
# Paths — safe to compute at import time (no env vars needed).
# BASE_DIR = project root (parent of api/)
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# ---------------------------------------------------------------------------
# Settings — defined as a class but NOT instantiated at import time.
# On Vercel, @vercel/python imports this module during the BUILD phase to find
# `handler`. Build-time env vars are NOT the same as runtime env vars.
# Instantiating Settings() here would raise ValidationError and crash the
# import → no `handler` found → no function deployed → 404 forever.
# ---------------------------------------------------------------------------
class Settings(BaseSettings):
    gemini_api_key: str = Field(..., validation_alias="GEMINI_API_KEY")
    gemini_model: str = Field("gemini-2.5-flash", validation_alias="GEMINI_MODEL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Lazy singleton — first call initialises and validates env vars."""
    return Settings()

# ---------------------------------------------------------------------------
# Gemini client — also lazy; depends on settings.
# google imports are deferred inside the function for the same reason.
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def get_gemini_client():
    from google import genai
    return genai.Client(api_key=get_settings().gemini_api_key)

def get_genai_types():
    from google.genai import types as genai_types
    return genai_types

def get_api_error_class():
    from google.genai.errors import APIError
    return APIError

# ---------------------------------------------------------------------------
# FastAPI app — safe to create at import time (no env vars needed here).
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Shiva Thavani | AI Engineer Portfolio",
    description="Vercel-deployed FastAPI app with Gemini-powered RAG assistant.",
    version="1.0.0",
)

static_dir = BASE_DIR / "static"
try:
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
except Exception as e:
    print(f"Warning: Could not mount static files: {e}")

templates = None
templates_dir = BASE_DIR / "templates"
if templates_dir.exists():
    templates = Jinja2Templates(directory=str(templates_dir))

try:
    from data.portfolio_data import PORTFOLIO
except ImportError:
    PORTFOLIO = {}

# ---------------------------------------------------------------------------
# Streaming RAG generator
# ---------------------------------------------------------------------------
async def response_generator(question: str):
    """
    Yields self-contained JSON lines:
      {"type": "status",  "text": "..."}   — loader filler lines
      {"type": "content", "text": "..."}   — final answer (markdown)
      {"type": "error",   "text": "..."}   — error message
    """
    q_lower = question.lower()

    fillers = ["Searching Shiva's career graph..."]

    if any(x in q_lower for x in ["atlassian", "autodesk", "thomson", "reuters",
                                    "ey", "company", "companies", "where"]):
        fillers.append("Cross-referencing Atlassian, Autodesk, Thomson Reuters, EY...")
    else:
        fillers.append("Pulling context from 4 companies, 5 years, 0 fluff...")

    if any(x in q_lower for x in ["gpu", "cost", "scale", "performance",
                                    "throughput", "azureml", "cuda"]):
        fillers.append("Retrieving from the ML engineer who optimized GPUs at 2.5x...")
        fillers.append("Fetching from the guy who reduced GPU costs by 30%...")
    else:
        fillers.append("Scanning career vectors... strong signal found...")
        fillers.append("One moment — running this through 5 years of prod ML...")

    fillers.append("This answer is RAG-grounded, not hallucinated...")
    fillers.append("Found the relevant experience. Composing answer...")

    for filler in fillers:
        yield json.dumps({"type": "status", "text": filler}) + "\n"
        await asyncio.sleep(0.45)

    knowledge_path = BASE_DIR / "data" / "shiva_knowledge_base.txt"
    if not knowledge_path.exists():
        yield json.dumps({"type": "error",
                          "text": "Portfolio knowledge base not found on server."}) + "\n"
        return

    try:
        knowledge = knowledge_path.read_text(encoding="utf-8")
    except Exception as exc:
        yield json.dumps({"type": "error",
                          "text": f"Could not read knowledge base: {exc}"}) + "\n"
        return

    prompt = f"""
You are Shiva Thavani's AI portfolio assistant.

Use only the knowledge base below to answer. Do not mention sources, citations,
the knowledge base, hidden context, or documents. If the answer is not covered,
say that you do not have enough information in Shiva's profile.

Return a clean, recruiter-friendly Markdown response:
1. One concise opening sentence summarising the answer.
2. A blank line.
3. Three to five short bullet points (using `- `) highlighting metrics, tools, or impact.

No long paragraphs. Use "Shiva" unless the question is directed at him personally.

Question:
{question}

Knowledge base:
{knowledge}
"""

    def _call_gemini() -> str:
        settings = get_settings()
        client = get_gemini_client()
        genai_types = get_genai_types()
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=genai_types.GenerateContentConfig(temperature=0.35),
        )
        return response.text or ""

    APIError = get_api_error_class()
    try:
        loop = asyncio.get_running_loop()
        full_text = await loop.run_in_executor(None, _call_gemini)
        if full_text.strip():
            yield json.dumps({"type": "content", "text": full_text}) + "\n"
        else:
            yield json.dumps({"type": "error",
                              "text": "Gemini returned an empty response."}) + "\n"
    except APIError as exc:
        yield json.dumps({"type": "error", "text": f"Gemini API error: {exc}"}) + "\n"
    except Exception as exc:
        yield json.dumps({"type": "error", "text": f"Unexpected error: {exc}"}) + "\n"


# ---------------------------------------------------------------------------
# Request model
# ---------------------------------------------------------------------------
class AskRequest(BaseModel):
    question: str = Field(..., min_length=1)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/")
async def home(request: Request):
    if not templates:
        return JSONResponse(status_code=500, content={"error": "Templates not found."})
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "portfolio": PORTFOLIO, "seo": PORTFOLIO.get("seo", {})},
    )


@app.get("/resume")
async def resume():
    path = BASE_DIR / "static" / "resume" / "Shiva_Resume.pdf"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Resume PDF not found.")
    return FileResponse(str(path), media_type="application/pdf",
                        filename="Shiva_Resume.pdf")


@app.get("/health")
async def health():
    # get_settings() is safe here — only called at request time on Vercel
    return {"status": "ok", "service": "portfolio", "model": get_settings().gemini_model}


@app.post("/api/ask")
async def ask_resume(payload: AskRequest):
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    return StreamingResponse(
        response_generator(question),
        media_type="text/plain",
        headers={"X-Accel-Buffering": "no",
                 "Cache-Control": "no-cache"},
    )


@app.get("/debug")
async def debug():
    return {
        "base_dir": str(BASE_DIR),
        "static_exists": (BASE_DIR / "static").exists(),
        "templates_exists": (BASE_DIR / "templates").exists(),
        "knowledge_exists": (BASE_DIR / "data" / "shiva_knowledge_base.txt").exists(),
        "gemini_api_key_set": bool(os.getenv("GEMINI_API_KEY")),
    }


# ---------------------------------------------------------------------------
# Vercel entrypoint
#
# @vercel/python scans this module at BUILD time to find `handler`.
# Everything above this line must be importable with NO env vars present
# (Vercel Dashboard env vars are injected at runtime, not build time).
# Mangum converts Vercel's Lambda-style invocation into ASGI for FastAPI.
# ---------------------------------------------------------------------------
handler = Mangum(app, lifespan="off")