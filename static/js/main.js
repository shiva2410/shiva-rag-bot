const navbar = document.querySelector("#navbar");
const menuToggle = document.querySelector("#menu-toggle");
const mobileMenu = document.querySelector("#mobile-menu");
const navLinks = [...document.querySelectorAll(".nav-link")];
const askForm = document.querySelector("#ask-form");
const askInput = document.querySelector("#ask-input");
const answerBox = document.querySelector("#assistant-answer");

function updateNavbar() {
  navbar?.classList.toggle("scrolled", window.scrollY > 12);
}

function setActiveLink() {
  const sections = ["about", "experience", "skills", "projects", "achievements", "contact"];
  let active = "";
  sections.forEach((id) => {
    const section = document.getElementById(id);
    if (section && section.getBoundingClientRect().top < 180) {
      active = id;
    }
  });
  navLinks.forEach((link) => {
    link.classList.toggle("active", link.getAttribute("href") === `#${active}`);
  });
}

function revealOnScroll() {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("visible");
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12 });

  document.querySelectorAll(".reveal").forEach((element, index) => {
    element.style.transitionDelay = `${Math.min(index % 5, 4) * 55}ms`;
    observer.observe(element);
  });
}

function renderMarkdown(text) {
  const lines = text.split("\n");
  let html = "";
  let inList = false;

  for (let line of lines) {
    const trimmed = line.trim();
    if (!trimmed) {
      if (inList) {
        html += "</ul>";
        inList = false;
      }
      continue;
    }

    if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
      if (!inList) {
        html += "<ul>";
        inList = true;
      }
      const content = trimmed.substring(2)
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>');
      html += `<li>${content}</li>`;
    } else {
      if (inList) {
        html += "</ul>";
        inList = false;
      }
      const content = trimmed
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>');
      html += `<p>${content}</p>`;
    }
  }
  if (inList) {
    html += "</ul>";
  }
  return html;
}

async function askResume(question) {
  if (!question.trim()) return;

  const panel = document.getElementById("assistant-panel");
  if (panel) {
    panel.style.display = "block";
  }

  // Reset the answer box to a neutral loading message — no black box yet
  answerBox.innerHTML = `<p class="loading-hint" style="color:#94a3b8;font-family:'JetBrains Mono',monospace;font-size:0.82rem;">⬡ Initialising AI assistant...</p>`;
  answerBox.classList.add("loading");

  let tracker = null;       // created lazily on first status message
  let answerContainer = null;
  let activeStatusEl = null;
  let fullAnswerText = "";

  function ensureTracker() {
    if (tracker) return;
    answerBox.innerHTML = `
      <div class="status-tracker" id="status-tracker"></div>
      <div class="stream-answer" id="stream-answer" style="display:none"></div>
    `;
    tracker = document.getElementById("status-tracker");
    answerContainer = document.getElementById("stream-answer");
  }

  function markActiveDone() {
    if (!activeStatusEl) return;
    activeStatusEl.classList.remove("active");
    activeStatusEl.classList.add("done");
    const icon = activeStatusEl.querySelector(".status-icon");
    if (icon) icon.innerHTML = '<span class="status-icon-check">✓</span>';
    activeStatusEl = null;
  }

  try {
    const response = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });

    if (!response.ok) throw new Error(`Server error ${response.status}`);

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Split on newlines; keep any incomplete trailing line in the buffer
      const lines = buffer.split("\n");
      buffer = lines.pop();

      for (const raw of lines) {
        const line = raw.trim();
        if (!line) continue;

        let msg;
        try {
          msg = JSON.parse(line);
          console.log("[stream]", msg);  // DEBUG: remove after confirming stream works
        } catch {
          console.warn("[stream] unparseable line:", line);  // DEBUG
          continue; // skip malformed lines silently
        }

        if (msg.type === "status") {
          ensureTracker();
          markActiveDone();

          const item = document.createElement("div");
          item.className = "status-item active";
          item.innerHTML = `
            <span class="status-icon"><span class="status-icon-spinner"></span></span>
            <span>${msg.text}</span>
          `;
          tracker.appendChild(item);
          activeStatusEl = item;
          tracker.scrollTop = tracker.scrollHeight;

        } else if (msg.type === "content") {
          ensureTracker();
          markActiveDone();

          answerContainer.style.display = "";
          fullAnswerText += msg.text;
          answerContainer.innerHTML = renderMarkdown(fullAnswerText);

        } else if (msg.type === "error") {
          throw new Error(msg.text);
        }
      }
    }

    markActiveDone();
    answerBox.classList.remove("loading");

    // Dynamic UI transition: move suggestions below answer & empty input
    const suggestionRow = document.getElementById("suggestion-row");
    const assistantPanel = document.getElementById("assistant-panel");
    if (suggestionRow && assistantPanel) {
      assistantPanel.parentNode.insertBefore(suggestionRow, assistantPanel.nextSibling);
    }
    if (askInput) {
      askInput.value = "";
    }

  } catch (error) {
    answerBox.classList.remove("loading");
    answerBox.innerHTML = `
      <p style="color:#ef4444;font-weight:700;margin-bottom:0.5rem;">⚠ Generation error</p>
      <p style="color:#64748b;font-size:0.875rem;">${error.message || "Failed to reach the portfolio assistant."}</p>
    `;
  }
}


/* ==========================================================================
   EASTER EGGS IMPLEMENTATION
   ========================================================================== */

// 1. Antigravity floating elements mode
function toggleAntigravity() {
  const isActive = document.body.classList.toggle("antigravity-active");
  
  document.querySelectorAll(".glass-card, .project-card, .timeline-card, .skill-badge").forEach((el, index) => {
    if (isActive) {
      const duration = 4 + (index % 4) * 0.75;
      el.style.setProperty("--float-duration", `${duration}s`);
    } else {
      el.style.removeProperty("--float-duration");
    }
  });

  const panel = document.getElementById("assistant-panel");
  if (panel) {
    panel.style.display = "block";
    answerBox.classList.remove("terminal-console");
    answerBox.innerHTML = isActive 
      ? `<div style="font-family:'JetBrains Mono',monospace;color:#10b981;font-weight:700;">✦ [ANTIGRAVITY MODE ACTIVATED]</div>
         <p style="color:#64748b;font-size:0.875rem;margin-top:0.5rem;">All layout cards have lost gravity! Bobbing floating state active. Double-click the logo again or type <strong>/normal</strong> to land them safely.</p>`
      : `<div style="font-family:'JetBrains Mono',monospace;color:#475569;font-weight:700;">✦ Antigravity elements safely landed.</div>`;
  }
}

// 2. Secret Dev Mode Hacker CLI Terminal console
function triggerTerminalConsole() {
  const panel = document.getElementById("assistant-panel");
  if (panel) {
    panel.style.display = "block";
  }
  
  answerBox.innerHTML = "";
  answerBox.classList.add("terminal-console");
  
  const terminalLines = [
    { text: "SHIVA THAVANI AI ENGINEER ROOT KERNEL v2.5.0-PROD", type: "white" },
    { text: "==================================================", type: "white" },
    { text: "> Initializing serverless security override...", type: "blue" },
    { text: "> Bypassing standard RAG query filters... [OK]", type: "green" },
    { text: "> Securing SSH tunnel link to Autodesk AzureML servers...", type: "blue" },
    { text: "> Connected to Autodesk CUDA inference proxy (2.5x throughput enabled)...", type: "green" },
    { text: "> Accessing Thomson Reuters MLOps platform registries...", type: "blue" },
    { text: "> De-risked production model registry loaded: [LLaMA-3, Claude-3, GPT-4]", type: "yellow" },
    { text: "> Grounding current core context vectors...", type: "blue" },
    { text: "  | 15+ production AI systems shipped successfully", type: "green" },
    { text: "  | $500K+ in GPU/infra spend optimized (30% enterprise spend)", type: "green" },
    { text: "  | ~40% reduction in MTTR via CSM-Rovo agentic support", type: "green" },
    { text: "  | 40% resolution rate in complex support workflows using AI Agent", type: "green" },
    { text: "> Establishing active Rovo-Agent workflows via LangGraph...", type: "blue" },
    { text: "> [SUCCESS] Shiva Thavani DevMode Console unlocked! Enter '/antigravity' or normal questions.", type: "green" }
  ];
  
  let i = 0;
  function printNextLine() {
    if (i < terminalLines.length) {
      const line = terminalLines[i];
      const p = document.createElement("p");
      if (line.type === "green") p.className = "terminal-green";
      else if (line.type === "yellow") p.className = "terminal-yellow";
      else if (line.type === "white") p.className = "terminal-white";
      
      p.textContent = line.text;
      answerBox.appendChild(p);
      answerBox.scrollTop = answerBox.scrollHeight;
      i++;
      setTimeout(printNextLine, 180);
    } else {
      const blink = document.createElement("span");
      blink.className = "terminal-blink";
      answerBox.appendChild(blink);
      
      // Move suggestion chips and clear
      const suggestionRow = document.getElementById("suggestion-row");
      const assistantPanel = document.getElementById("assistant-panel");
      if (suggestionRow && assistantPanel) {
        assistantPanel.parentNode.insertBefore(suggestionRow, assistantPanel.nextSibling);
      }
      if (askInput) {
        askInput.value = "";
      }
    }
  }
  
  printNextLine();
}


menuToggle?.addEventListener("click", () => {
  mobileMenu.classList.toggle("hidden");
});

document.querySelectorAll("#mobile-menu a").forEach((link) => {
  link.addEventListener("click", () => mobileMenu.classList.add("hidden"));
});

// Brand Logo Double-Click Antigravity toggle
const logo = document.getElementById("brand-logo");
logo?.addEventListener("dblclick", (e) => {
  e.preventDefault();
  toggleAntigravity();
});

askForm?.addEventListener("submit", (event) => {
  event.preventDefault();
  const query = askInput.value.trim().toLowerCase();
  
  if (query === "/sudo dev" || query === "/matrix" || query === "/terminal" || query === "/help" || query === "/dev") {
    triggerTerminalConsole();
  } else if (query === "/antigravity" || query === "/float") {
    if (!document.body.classList.contains("antigravity-active")) {
      toggleAntigravity();
    }
    askInput.value = "";
  } else if (query === "/normal" || query === "/land") {
    if (document.body.classList.contains("antigravity-active")) {
      toggleAntigravity();
    }
    askInput.value = "";
  } else {
    answerBox.classList.remove("terminal-console");
    askResume(askInput.value);
  }
});

document.querySelectorAll(".suggestion-chip").forEach((button) => {
  button.addEventListener("click", () => {
    const question = button.dataset.question || button.textContent;
    askInput.value = question;
    const query = question.trim().toLowerCase();
    if (query === "/sudo dev" || query === "/matrix" || query === "/terminal" || query === "/help" || query === "/dev") {
      triggerTerminalConsole();
    } else {
      answerBox.classList.remove("terminal-console");
      askResume(question);
    }
  });
});

window.addEventListener("scroll", () => {
  updateNavbar();
  setActiveLink();
}, { passive: true });

updateNavbar();
setActiveLink();
revealOnScroll();
