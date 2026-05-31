# Shiva Thavani AI Engineer Portfolio

Production-ready FastAPI portfolio website deployed on Vercel, built with Jinja2 templates, Tailwind CSS CDN, vanilla JavaScript animations, and a Google-search-inspired AI engineer interface powered by a Gemini RAG assistant.

## Features

- **FastAPI Backend**: Reusable data-driven portfolio endpoints.
- **Vercel Serverless ready**: Deployed as a Python serverless function via `Mangum` ASGI adapter.
- **Jinja2 component templates**: Clean server-side HTML rendering.
- **Tailwind CSS & Vanilla JS**: Sleek, modern responsive styling and micro-animations with minimal client footprint.
- **Gemini-powered RAG assistant**: An interactive recruiter assistant at `/api/ask` using the standard `google-generativeai` SDK.
- **Settings Validation**: Auto-validating config and env variables via `pydantic-settings` on startup.
- **SEO & Social Share**: Configured with meta and Open Graph tags.

## Project Structure

```text
portfolio/
├── api/
│   └── index.py            # Vercel entrypoint & FastAPI App
├── data/
│   ├── portfolio_data.py   # Portfolio structured data
│   ├── shiva_knowledge_base.txt # AI assistant knowledge source
│   └── Shiva-Thavani-Info.docx  # Full source CV documentation
├── static/
│   ├── css/styles.css      # Portfolio styling
│   ├── js/main.js          # Interactive frontend & assistant handler
│   ├── images/             # Static graphics
│   └── resume/
│       └── Shiva_Resume.pdf# Downloadable resume PDF
├── templates/
│   ├── base.html           # Main base structure
│   ├── index.html          # Portfolio view
│   └── components/         # Modular template pieces
├── .env                    # Local environment settings (ignored)
├── .gitignore              # Files ignored by git
├── requirements.txt        # Serverless packages list
└── vercel.json             # Vercel deployment configurations
```

## Local Development

### 1. Clone & Setup Environment

```bash
cd portfolio
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Local Variables

Create a `.env` file in the root directory (already added to `.gitignore`):

```env
GEMINI_API_KEY="your-actual-api-key"
GEMINI_MODEL="gemini-1.5-flash"
```

> [!IMPORTANT]
> The application will validate environment variables on startup. If `GEMINI_API_KEY` is not present in `.env` or system environment variables, a `RuntimeError` will be raised.

### 3. Start local development server

```bash
uvicorn api.index:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

---

## Vercel Deployment

Deploying the application to Vercel is seamless and leverages the `@vercel/python` serverless runtime.

### 1. Prerequisite Settings
Make sure you have:
1. All changes committed to a Git repository (GitHub/GitLab/Bitbucket).
2. A Vercel account connected to your Git provider.

### 2. Configure Vercel Project
- Import the repository in the **Vercel Dashboard**.
- Set the **Framework Preset** to **Other** (Vercel automatically detects the `vercel.json` config).
- In **Environment Variables**, add:
  - `GEMINI_API_KEY`: Your Google Gemini API Key.
  - `GEMINI_MODEL`: `gemini-1.5-flash` (Optional, defaults to `gemini-1.5-flash`).

### 3. Deploy
Click **Deploy**. Vercel will:
- Read `vercel.json` and build the serverless function in `api/index.py` using `requirements.txt`.
- Rewrite all routes matching `/(.*)` to point directly to `api/index` (handled by the Mangum adapter wrapper).

---

## Customization

- **Resume Knowledge**: Sourced from `data/shiva_knowledge_base.txt`. Update this text file when there are new achievements or changes in Shiva's CV.
- **Interface Content**: Modifying `data/portfolio_data.py` will automatically update all fields (experience, skills, metric highlights, projects, achievements, etc.) throughout the website.
- **Frontend Interaction**: Check `static/js/main.js` to modify how requests are sent to `/api/ask` and how assistant answers are dynamically loaded.

---

## SEO, Google Search Console & Backlink Strategy

This portfolio is highly optimized to rank #1 on Google searches for **"Shiva Thavani"**, **"Shiva Thavani AI Engineer"**, **"Shiva Thavani Machine Learning Engineer"**, **"Shiva Thavani GenAI Engineer"**, and **"Shiva Thavani LLMOps"**.

### 1. Google Search Console & Domain Verification

To claim your website on Google and ensure rapid indexing:

1. **Add Property**:
   - Go to [Google Search Console](https://search.google.com/search-console/about).
   - Click **Add Property** -> Select **URL prefix** and enter `https://shiva-rag-bot.vercel.app/`.
2. **Verify Domain Ownership**:
   - Verify ownership using Vercel DNS settings, HTML tag method, or Google Analytics.
   - Click **Verify** in Search Console.
3. **Submit Sitemap**:
   - In Search Console, click **Sitemaps** on the left menu.
   - Under **Add a new sitemap**, type `sitemap.xml`.
   - Click **Submit**. Google will read the sitemap from `https://shiva-rag-bot.vercel.app/sitemap.xml` weekly to keep your pages indexed.
4. **Force Indexing**:
   - If your site isn't showing up yet, paste your homepage URL `https://shiva-rag-bot.vercel.app/` into the Search Console top search bar.
   - Click **Request Indexing** to force Google's bot to crawl your portfolio immediately.

---

### 2. Backlink Authority Strategy (SEO Powerhouse)

Google rankings rely heavily on authority. Build high-quality backlinks to guarantee top positions:

1. **LinkedIn Integration**:
   - Add `https://shiva-rag-bot.vercel.app/` in the **Contact Info** section of your profile.
   - Add your custom portfolio link directly underneath your LinkedIn headline (using LinkedIn's link button feature).
   - Write a post announcing your portfolio deployment and link it.
2. **GitHub Integration**:
   - Add the website URL `https://shiva-rag-bot.vercel.app/` in the **About** section of your GitHub profile repo (your profile README).
   - Link it in the README files of all your major repositories.
3. **Medium & Dev.to Backlinks (Crucial)**:
   - Go to your popular Medium articles (e.g., your *Solar Panel Detection* or *Document Verification* article).
   - Edit the article to include a backlink, e.g., *"Shiva Thavani is an AI Engineer. Explore his interactive AI-powered portfolio at [shiva-rag-bot.vercel.app](https://shiva-rag-bot.vercel.app/)."*
   - Medium links pass high domain authority and will rank your portfolio rapidly.
4. **Lighthouse & Performance SEO**:
   - High-quality, fast-loading portfolios rank higher. Native lazy-loading (`loading="lazy"`) and optimized next-gen image types in this portfolio guarantee 95+ scores on Lighthouse mobile and desktop audits.
