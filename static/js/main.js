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

  // Reset the answer box to a neutral loading message — no black box yet
  answerBox.innerHTML = `<p class="loading-hint" style="color:#94a3b8;font-family:'JetBrains Mono',monospace;font-size:0.82rem;">⬡ Initialising Gemini assistant...</p>`;
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

  } catch (error) {
    answerBox.classList.remove("loading");
    answerBox.innerHTML = `
      <p style="color:#ef4444;font-weight:700;margin-bottom:0.5rem;">⚠ Generation error</p>
      <p style="color:#64748b;font-size:0.875rem;">${error.message || "Failed to reach the portfolio assistant."}</p>
    `;
  }
}



menuToggle?.addEventListener("click", () => {
  mobileMenu.classList.toggle("hidden");
});

document.querySelectorAll("#mobile-menu a").forEach((link) => {
  link.addEventListener("click", () => mobileMenu.classList.add("hidden"));
});

askForm?.addEventListener("submit", (event) => {
  event.preventDefault();
  askResume(askInput.value);
});

document.querySelectorAll(".suggestion-chip").forEach((button) => {
  button.addEventListener("click", () => {
    const question = button.dataset.question || button.textContent;
    askInput.value = question;
    askResume(question);
  });
});

window.addEventListener("scroll", () => {
  updateNavbar();
  setActiveLink();
}, { passive: true });

updateNavbar();
setActiveLink();
revealOnScroll();
