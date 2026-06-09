import os
import sys
import json
import random
import asyncio
from pathlib import Path
from functools import lru_cache
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Response
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
    description="Vercel-deployed FastAPI app with AI-powered RAG assistant.",
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
# ---------------------------------------------------------------------------
# Global database of dynamic loading fillers (100 variants to prevent repetition)
# ---------------------------------------------------------------------------
FILLERS = [
    # ── PERSONAL / PERSONALITY (1-25) ──────────────────────────────
    "Flipping through Shiva's career pages...",
    "Let me check what Shiva actually shipped...",
    "Consulting the source of truth...",
    "Asking the guy who won 4 hackathons...",
    "Pulling from a career built across 4 companies...",
    "Tracing the journey from EY to Atlassian...",
    "5 years of ML work, finding the right chapter...",
    "Checking what the Gold Medalist has to say...",
    "Let me find the most relevant chapter...",
    "Shiva's done a lot here, fetching the right thread...",
    "Cross-referencing roles, projects and impact metrics...",
    "Digging into the Atlassian chapter...",
    "Pulling this from 5 years of production ML...",
    "One sec — there's a lot to unpack here...",
    "This one spans multiple roles, fetching...",
    "Searching across 4 companies worth of experience...",
    "Navigating the career timeline...",
    "Let me find the chapter where Shiva crushed it...",
    "Connecting the dots across roles...",
    "Fetching from someone who's actually shipped this stuff...",
    "Checking Shiva's track record on this...",
    "Pulling context from a guy who's been in the trenches...",
    "The answer is in here somewhere, hold on...",
    "Retrieving from the ML engineer who's done this for real...",
    "Let me check what actually happened here...",

    # ── TECHNICAL / RAG (26-55) ────────────────────────────────────
    "Embedding your query into vector space...",
    "Semantic search across career context...",
    "Fetching relevant chunks from knowledge base...",
    "Re-ranking retrieved passages...",
    "Grounding response in resume context...",
    "Running RAG pipeline on 5 years of experience...",
    "Knowledge graph traversal in progress...",
    "Top match found. Synthesizing answer...",
    "Dense retrieval complete. Re-ranking now...",
    "Scanning career vectors... strong signal found...",
    "Context window loaded. Generating response...",
    "Similarity search complete. Composing answer...",
    "Hybrid retrieval engaged...",
    "Fetching top-k chunks from career embeddings...",
    "Cross-encoder re-ranking in progress...",
    "Retrieving from semantic index...",
    "Query understood. Searching knowledge base...",
    "Context retrieved. Grounding response now...",
    "Running inference on retrieved context...",
    "Chunk relevance scored. Generating answer...",
    "Vector similarity > 0.95. Proceeding...",
    "LLM context window populated. Thinking...",
    "RAG pipeline complete. Composing response...",
    "Knowledge base indexed. Fetching answer...",
    "Retrieval complete. No hallucinations, promise...",
    "Passage scores computed. Top match loaded...",
    "Document chunks ranked. Assembling answer...",
    "Semantic similarity check complete...",
    "Context compression applied. Generating...",
    "Attention heads focused on your query...",

    # ── HUMOR (56-75) ──────────────────────────────────────────────
    "Asking Shiva so you don't have to...",
    "Fewer hallucinations than your average LLM, promise...",
    "This is faster than a LinkedIn stalk...",
    "Shiva's resume is big. Give me a moment...",
    "Retrieving... (Shiva has done a lot, okay?)...",
    "Not making this up — actually checking the context...",
    "One moment while I Google the recruiter...",
    "Hold on, even GPT-5 needs a second for this...",
    "Loading career highlights. There are many...",
    "Consulting the world's most specific knowledge base...",
    "RAG-ing through the resume so you don't have to...",
    "Checking if Shiva actually shipped this or just added it to LinkedIn...",
    "Spoiler: he shipped it...",
    "This answer is grounded, not vibed...",
    "Less hallucination, more citation...",
    "Finding the needle in a very impressive haystack...",
    "Brb, reading 5 years of career history...",
    "Loading... (Shiva's career is not a short read)...",
    "Fact-checking against the actual resume...",

    # ── IMPACT / METRICS FLAVORED (76-88) ─────────────────────────
    "Retrieving from the engineer who cut GPU costs by 30%...",
    "Fetching from the guy who hit 2.5x GPU throughput...",
    "Pulling from 10,000+ AI-assisted conversations worth of context...",
    "Consulting the architect of CSM-Rovo...",
    "Checking the record of the guy who reduced manual work by 45%...",
    "Pulling from the engineer who supported 200+ data scientists...",
    "Retrieving from someone with 90%+ accuracy on document AI...",
    "Fetching from the 4x hackathon winner...",
    "Loading context from the Gold Medalist...",
    "Asking the engineer with real production LLM deployments...",
    "Retrieving from the guy who shipped agentic AI before it was cool...",
    "Consulting 5 years of quantified impact...",
    "Pulling from a career with actual numbers, not just buzzwords...",

    # ── MIXED / HYBRID (89-100) ────────────────────────────────────
    "Pulling context from 4 companies, 5 years, 0 fluff...",
    "Found the relevant experience. Composing answer...",
    "This answer is RAG-grounded, not hallucinated...",
    "Fetching from the knowledge base, not thin air...",
    "Scanning career graph... strong signal detected...",
    "Cross-referencing Atlassian, Autodesk, Thomson Reuters, EY...",
    "Context loaded from 5 years of production ML work...",
    "Retrieving experience. Please hold — it's extensive...",
    "Knowledge base hit. Assembling recruiter-friendly answer...",
    "Grounding in reality, not buzzwords...",
    "Pulling from the source — not GPT's imagination...",
    "Career context loaded. Answer incoming...",
]

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
    
    # 1. Compile contextually matched fillers
    matched = []
    if any(x in q_lower for x in ["atlassian", "autodesk", "thomson", "reuters", "ey", "company", "companies", "where"]):
        matched.extend([
            "Cross-referencing Atlassian, Autodesk, Thomson Reuters, EY...",
            "Pulling from a career built across 4 companies...",
            "Searching across 4 companies worth of experience...",
            "Tracing the journey from EY to Atlassian...",
            "Digging into the Atlassian chapter..."
        ])
    if any(x in q_lower for x in ["gpu", "cost", "scale", "performance", "throughput", "azureml", "cuda"]):
        matched.extend([
            "Retrieving from the engineer who cut GPU costs by 30%...",
            "Fetching from the guy who hit 2.5x GPU throughput...",
            "Pulling from the engineer who supported 200+ data scientists..."
        ])
    if any(x in q_lower for x in ["hackathon", "prize", "winner", "sih", "bosch"]):
        matched.extend([
            "Asking the guy who won 4 hackathons...",
            "Fetching from the 4x hackathon winner..."
        ])
    if any(x in q_lower for x in ["gold", "medalist", "academic", "scholarship", "tiet"]):
        matched.extend([
            "Checking what the Gold Medalist has to say...",
            "Loading context from the Gold Medalist..."
        ])
    if any(x in q_lower for x in ["agent", "agentic", "langgraph", "rovo", "csm"]):
        matched.extend([
            "Consulting the architect of CSM-Rovo...",
            "Retrieving from the guy who shipped agentic AI before it was cool..."
        ])
    if any(x in q_lower for x in ["rag", "vector", "semantic", "search", "embeddings"]):
        matched.extend([
            "Embedding your query into vector space...",
            "Semantic search across career context...",
            "Fetching relevant chunks from knowledge base...",
            "Re-ranking retrieved passages...",
            "Running RAG pipeline on 5 years of experience...",
            "Scanning career vectors... strong signal found...",
            "RAG-ing through the resume so you don't have to..."
        ])
    if any(x in q_lower for x in ["research", "paper", "published", "publication","machine learning","deep learning","computer vision","springer", "face recognition", "piir", "pose"]):
        matched.extend([
            "Pulling from the Springer-published researcher...",
            "Checking across published research and real-world shipped systems...",
            "Fetching from research papers and production deployments alike...",
            "Retrieving from published research and industry production deployments..."
        ])

    # 2. Select distinct fillers: take up to 2 context matches, fill up to 5 with others
    selected = []
    if matched:
        matched = list(set(matched))
        selected.extend(random.sample(matched, min(len(matched), 2)))
        
    remaining = [f for f in FILLERS if f not in selected]
    needed = 5 - len(selected)
    selected.extend(random.sample(remaining, needed))
    
    # Shuffle organic fillers
    random.shuffle(selected)
    
    # 3. Choose a beautiful final closer and append
    satisfying_closers = [
        "Found the relevant experience. Composing answer...",
        "RAG pipeline complete. Composing response...",
        "Knowledge base hit. Assembling recruiter-friendly answer...",
        "Career context loaded. Answer incoming...",
        "Similarity search complete. Composing answer..."
    ]
    # Filter out closers from the first 4 slots to prevent duplicate, and slice down to 4
    selected = [s for s in selected if s not in satisfying_closers][:4]
    selected.append(random.choice(satisfying_closers))

    for filler in selected:
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
        APIError = get_api_error_class()
        
        primary_model = settings.gemini_model
        fallback_model = "gemini-2.5-flash-lite"
        
        try:
            response = client.models.generate_content(
                model=primary_model,
                contents=prompt,
                config=genai_types.GenerateContentConfig(temperature=0.35),
            )
            return response.text or ""
        except APIError as exc:
            if primary_model != fallback_model:
                print(f"[GEMINI FALLBACK] Primary model '{primary_model}' failed: {exc}. Trying fallback '{fallback_model}'...")
                try:
                    response = client.models.generate_content(
                        model=fallback_model,
                        contents=prompt,
                        config=genai_types.GenerateContentConfig(temperature=0.35),
                    )
                    return response.text or ""
                except Exception as fallback_exc:
                    print(f"[GEMINI FALLBACK ERROR] Fallback model '{fallback_model}' also failed: {fallback_exc}")
                    raise fallback_exc
            raise exc

    APIError = get_api_error_class()
    try:
        loop = asyncio.get_running_loop()
        full_text = await loop.run_in_executor(None, _call_gemini)
        if full_text.strip():
            yield json.dumps({"type": "content", "text": full_text}) + "\n"
        else:
            yield json.dumps({"type": "error",
                              "text": "AI assistant returned an empty response."}) + "\n"
    except APIError as exc:
        yield json.dumps({"type": "error", "text": f"AI assistant API error: {exc}"}) + "\n"
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
    try:
        import urllib.parse
        country = request.headers.get("x-vercel-ip-country", "Unknown Country")
        region = request.headers.get("x-vercel-ip-country-region", "")
        city_encoded = request.headers.get("x-vercel-ip-city", "")
        city = urllib.parse.unquote(city_encoded) if city_encoded else "Unknown City"
        location = f"{city}, {region} ({country})" if region else f"{city} ({country})"
        
        referer = request.headers.get("referer", "")
        source = "Direct / Direct Input"
        if referer:
            ref_lower = referer.lower()
            if "linkedin.com" in ref_lower:
                source = "LinkedIn"
            elif "medium.com" in ref_lower:
                source = "Medium"
            elif "google.com" in ref_lower:
                source = "Google Search"
            elif "github.com" in ref_lower:
                source = "GitHub"
            elif "t.co" in ref_lower or "twitter.com" in ref_lower or "x.com" in ref_lower:
                source = "X / Twitter"
            else:
                source = referer

        user_agent = request.headers.get("user-agent", "Unknown Browser")
        print(f"[VISITOR LOG] 🚀 New Visit | Location: {location} | Source: {source} | User-Agent: {user_agent}")
    except Exception as e:
        print(f"[VISITOR LOG ERROR] Failed to log visitor: {e}")

    if not templates:
        return JSONResponse(status_code=500, content={"error": "Templates not found."})
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"portfolio": PORTFOLIO, "seo": PORTFOLIO.get("seo", {})},
    )


@app.api_route("/sitemap.xml", methods=["GET", "HEAD"])
async def sitemap():
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:schemaLocation="http://www.sitemaps.org/schemas/sitemap/0.9
                            http://www.sitemaps.org/schemas/sitemap/0.9/sitemap.xsd">
    <url>
        <loc>https://shiva-rag-bot.vercel.app/</loc>
        <lastmod>2026-06-03</lastmod>
        <changefreq>weekly</changefreq>
        <priority>1.0</priority>
    </url>
    <url>
        <loc>https://shiva-rag-bot.vercel.app/resume</loc>
        <lastmod>2026-06-03</lastmod>
        <changefreq>monthly</changefreq>
        <priority>0.8</priority>
    </url>
</urlset>"""
    return Response(content=xml_content, media_type="application/xml")


@app.api_route("/robots.txt", methods=["GET", "HEAD"])
async def robots_txt():
    txt_content = """User-agent: *
Allow: /

Sitemap: https://shiva-rag-bot.vercel.app/sitemap.xml"""
    return Response(content=txt_content, media_type="text/plain")


@app.api_route("/favicon.ico", methods=["GET", "HEAD"], include_in_schema=False)
async def serve_favicon():
    path = BASE_DIR / "static" / "images" / "favicon.svg"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Favicon not found.")
    return FileResponse(str(path), media_type="image/svg+xml")


@app.api_route("/favicon.png", methods=["GET", "HEAD"], include_in_schema=False)
async def serve_favicon_png():
    path = BASE_DIR / "static" / "images" / "favicon.svg"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Favicon not found.")
    return FileResponse(str(path), media_type="image/svg+xml")


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
async def ask_resume(payload: AskRequest, request: Request):
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
        
    try:
        import urllib.parse
        country = request.headers.get("x-vercel-ip-country", "Unknown Country")
        region = request.headers.get("x-vercel-ip-country-region", "")
        city_encoded = request.headers.get("x-vercel-ip-city", "")
        city = urllib.parse.unquote(city_encoded) if city_encoded else "Unknown City"
        location = f"{city}, {region} ({country})" if region else f"{city} ({country})"
        
        print(f"[QUERY LOG] 💬 AI Query | Location: {location} | Query: \"{question}\"")
    except Exception as e:
        print(f"[QUERY LOG ERROR] Failed to log query: {e}")

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