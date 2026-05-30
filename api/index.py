import os
import sys
import json
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from mangum import Mangum

# ---------------------------------------------------------------------------
# 1. Environment – load .env for local dev before reading any env vars
# ---------------------------------------------------------------------------
load_dotenv()

if not os.getenv("GEMINI_API_KEY"):
    raise RuntimeError("GEMINI_API_KEY is not set")

# ---------------------------------------------------------------------------
# 2. Settings (validated at startup by pydantic-settings)
# ---------------------------------------------------------------------------
class Settings(BaseSettings):
    gemini_api_key: str = Field(..., validation_alias="GEMINI_API_KEY")
    gemini_model: str = Field("gemini-2.5-flash", validation_alias="GEMINI_MODEL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()

# ---------------------------------------------------------------------------
# 3. Gemini client  (google-genai package — same as original app.py)
# ---------------------------------------------------------------------------
from google import genai
from google.genai import types as genai_types
from google.genai.errors import APIError

gemini_client = genai.Client(api_key=settings.gemini_api_key)

# ---------------------------------------------------------------------------
# 4. Paths – BASE_DIR is the project root (parent of api/)
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# ---------------------------------------------------------------------------
# 5. FastAPI app + mounts
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Shiva Thavani | AI Engineer Portfolio",
    description="Vercel-deployed FastAPI app with Gemini-powered RAG assistant.",
    version="1.0.0",
)

static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

templates = None
templates_dir = BASE_DIR / "templates"
if templates_dir.exists():
    templates = Jinja2Templates(directory=str(templates_dir))

try:
    from data.portfolio_data import PORTFOLIO
except ImportError:
    PORTFOLIO = {}

# ---------------------------------------------------------------------------
# 6. Streaming RAG generator
# ---------------------------------------------------------------------------
async def response_generator(question: str):
    """
    Yields self-contained JSON lines:
      {"type": "status",  "text": "..."}   — loader filler lines
      {"type": "content", "text": "..."}   — final answer (markdown)
      {"type": "error",   "text": "..."}   — error message
    """
    q_lower = question.lower()

    # Build context-aware filler sequence
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

    # --- emit fillers while Gemini warms up ---
    for filler in fillers:
        yield json.dumps({"type": "status", "text": filler}) + "\n"
        await asyncio.sleep(0.45)

    # --- load knowledge base ---
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

    # ------------------------------------------------------------------
    # IMPORTANT: generate_content() is a blocking synchronous call.
    # Running it in a thread via run_in_executor keeps the event loop
    # free so uvicorn can flush the status lines above to the browser
    # while Gemini is processing.
    # ------------------------------------------------------------------
    def _call_gemini() -> str:
        response = gemini_client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=genai_types.GenerateContentConfig(temperature=0.35),
        )
        return response.text or ""

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
# 7. Request model
# ---------------------------------------------------------------------------
class AskRequest(BaseModel):
    question: str = Field(..., min_length=1)


# ---------------------------------------------------------------------------
# 8. Routes
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
    return {"status": "ok", "service": "portfolio", "model": settings.gemini_model}


@app.post("/api/ask")
async def ask_resume(payload: AskRequest):
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    return StreamingResponse(
        response_generator(question),
        media_type="text/plain",
        headers={"X-Accel-Buffering": "no",   # disable nginx buffering
                 "Cache-Control": "no-cache"},
    )


# ---------------------------------------------------------------------------
# 9. Mangum handler for Vercel serverless
# ---------------------------------------------------------------------------
handler = Mangum(app)
