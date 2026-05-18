// ── State ───────────────────────────────────────────────────────────────────
const BACKEND_URL = 'http://localhost:8080';
let currentCardUrl   = '';
let currentUsername  = '';
let selectedPlatform = 'github';
let selectedTheme    = 'auto';
let selectedLayout   = 'standard';

// ── DOM refs ─────────────────────────────────────────────────────────────────
const usernameInput = document.getElementById('username-input');
const generateBtn   = document.getElementById('generate-btn');
const skeleton      = document.getElementById('skeleton');
const result        = document.getElementById('result');
const error         = document.getElementById('error');
const cardIframe    = document.getElementById('card-iframe');
const loadingText   = document.getElementById('loading-text');
const shareBtn      = document.getElementById('share-btn');

// ── Auth Bar ─────────────────────────────────────────────────────────────────
const GITHUB_LOGO_SVG = `<svg viewBox="0 0 98 96" xmlns="http://www.w3.org/2000/svg" width="13" height="13" fill="currentColor"><path fill-rule="evenodd" clip-rule="evenodd" d="M48.854 0C21.839 0 0 22 0 49.217c0 21.756 13.993 40.172 33.405 46.69 2.427.49 3.316-1.059 3.316-2.362 0-1.141-.08-5.052-.08-9.127-13.59 2.934-16.42-5.867-16.42-5.867-2.184-5.704-5.42-7.17-5.42-7.17-4.448-3.015.324-3.015.324-3.015 4.934.326 7.523 5.052 7.523 5.052 4.367 7.496 11.404 5.378 14.235 4.074.404-3.178 1.699-5.378 3.074-6.6-10.839-1.141-22.243-5.378-22.243-24.283 0-5.378 1.94-9.778 5.014-13.2-.485-1.222-2.184-6.275.486-13.038 0 0 4.125-1.304 13.426 5.052a46.97 46.97 0 0 1 12.214-1.63c4.125 0 8.33.571 12.213 1.63 9.302-6.356 13.427-5.052 13.427-5.052 2.67 6.763.97 11.816.485 13.038 3.155 3.422 5.015 7.822 5.015 13.2 0 18.905-11.404 23.06-22.324 24.283 1.78 1.548 3.316 4.481 3.316 9.126 0 6.6-.08 11.897-.08 13.526 0 1.304.89 2.853 3.316 2.364 19.412-6.52 33.405-24.935 33.405-46.691C97.707 22 75.788 0 48.854 0z"/></svg>`;
const GITLAB_LOGO_SVG = `<svg viewBox="0 0 380 380" xmlns="http://www.w3.org/2000/svg" width="13" height="13"><path fill="#e24329" d="M282.83 170.73l-.27-.69-26.14-68.22a6.81 6.81 0 00-2.69-3.24 7 7 0 00-8 .43 7 7 0 00-2.32 3.52l-17.65 54h-71.46l-17.65-54a6.86 6.86 0 00-2.32-3.52 7 7 0 00-8-.43 6.87 6.87 0 00-2.69 3.24L97.44 170l-.26.69a48.54 48.54 0 0016.1 56.1l.09.07.24.17 39.82 29.82 19.7 14.91 12 9.06a8.07 8.07 0 009.65 0l12-9.06 19.7-14.91 40.06-30 .1-.08a48.56 48.56 0 0016.14-56.04z"/><path fill="#fc6d26" d="M282.83 170.73l-.27-.69a88.3 88.3 0 00-35.15 15.8L190 229.25c19.55 14.79 36.57 27.64 36.57 27.64l40.06-30 .1-.08a48.56 48.56 0 0016.1-56.08z"/><path fill="#fca326" d="M153.43 256.89l19.7 14.91 12 9.06a8.07 8.07 0 009.65 0l12-9.06 19.7-14.91S209 244 190 229.25c-19.55 14.79-36.57 27.64-36.57 27.64z"/><path fill="#fc6d26" d="M132.58 185.84A88.19 88.19 0 0097.44 170l-.26.69a48.54 48.54 0 0016.1 56.1l.09.07.24.17 39.82 29.82S170 244 190 229.25z"/></svg>`;

const LINKEDIN_LOGO_SVG = `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" width="13" height="13" fill="#0A66C2"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>`;

async function initAuthBar() {
  const actionsEl = document.getElementById('auth-bar-actions');
  try {
    const res = await fetch(`${BACKEND_URL}/auth/me`, { credentials: 'include' });
    const data = await res.json();
    if (data.authenticated) {
      actionsEl.innerHTML = `
        <img src="${data.avatar_url}" class="auth-avatar" alt="${data.login}" title="${data.name || data.login}">
        <span class="auth-username">@${data.login}</span>
        <a href="${BACKEND_URL}/auth/logout" class="auth-btn auth-btn-logout">Sign Out</a>
      `;
    } else {
      actionsEl.innerHTML = `
        <span class="auth-sign-in-label">Sign in:</span>
        <a href="${BACKEND_URL}/auth/github" class="auth-btn auth-btn-provider auth-btn-github" title="Sign in with GitHub">${GITHUB_LOGO_SVG} GitHub</a>
        <a href="${BACKEND_URL}/auth/gitlab" class="auth-btn auth-btn-provider auth-btn-gitlab" title="Sign in with GitLab">${GITLAB_LOGO_SVG} GitLab</a>
        <a href="${BACKEND_URL}/auth/linkedin" class="auth-btn auth-btn-provider auth-btn-linkedin" title="Sign in with LinkedIn">${LINKEDIN_LOGO_SVG} LinkedIn</a>
      `;
    }
  } catch {
    actionsEl.innerHTML = '';
  }
}
initAuthBar();

// ── Platform Switcher ─────────────────────────────────────────────────────────
function setPlatform(p) {
  selectedPlatform = p;
  document.querySelectorAll('.platform-btn').forEach(b => b.classList.remove('active'));
  document.getElementById(`btn-${p}`).classList.add('active');
  const prefix = document.getElementById('input-prefix');

  const map = {
    github:    { prefix: 'github.com/',     placeholder: 'torvalds',       pad: '107px' },
    gitlab:    { prefix: 'gitlab.com/',     placeholder: 'gitlab-org',     pad: '105px' },
    linkedin:  { prefix: 'linkedin.com/in/', placeholder: 'williamhgates', pad: '143px' },
  };
  const cfg = map[p] || map.github;
  prefix.textContent = cfg.prefix;
  usernameInput.placeholder = cfg.placeholder;
  usernameInput.style.paddingLeft = cfg.pad;
}
// Set correct padding on initial load
setPlatform('github');

// ── Customization Panel ───────────────────────────────────────────────────────
function toggleCustomize() {
  const panel = document.getElementById('customize-panel');
  const arrow = document.getElementById('toggle-arrow');
  const open  = panel.classList.toggle('open');
  arrow.textContent = open ? '▾' : '▸';
}

function setTheme(btn) {
  selectedTheme = btn.dataset.theme;
  document.querySelectorAll('.theme-opt').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
}

function setLayout(btn) {
  selectedLayout = btn.dataset.layout;
  document.querySelectorAll('.layout-opt').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
}

// ── Enter key ─────────────────────────────────────────────────────────────────
usernameInput.addEventListener('keydown', e => {
  if (e.key === 'Enter') generateCard();
});

// ── Loading step messages ─────────────────────────────────────────────────────
const loadingSteps = [
  '🔍 Scraping profile...',
  '🤖 Analyzing with Gemini AI...',
  '🎨 Generating themed card...',
  '💾 Saving your dev card...',
  '⏳ Almost there...',
  '⏳ Still working, this can take up to 60s...',
];
let stepIndex = 0, stepInterval = null;

function startLoadingSteps() {
  stepIndex = 0;
  loadingText.textContent = loadingSteps[0];
  stepInterval = setInterval(() => {
    stepIndex = Math.min(stepIndex + 1, loadingSteps.length - 1);
    loadingText.textContent = loadingSteps[stepIndex];
  }, 8000);
}
function stopLoadingSteps() {
  if (stepInterval) clearInterval(stepInterval);
  stepInterval = null;
}

// ── Main generate function ────────────────────────────────────────────────────
async function generateCard() {
  const username = usernameInput.value.trim();
  if (!username) {
    usernameInput.focus();
    usernameInput.style.borderColor = 'var(--red)';
    setTimeout(() => usernameInput.style.borderColor = '', 1500);
    return;
  }

  generateBtn.disabled = true;
  generateBtn.innerHTML = '<div class="loading-spinner" style="width:14px;height:14px;border-width:2px;"></div> Generating...';
  skeleton.classList.add('active');
  result.classList.remove('active');
  error.classList.remove('active');
  startLoadingSteps();

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 120000);

    const response = await fetch(`${BACKEND_URL}/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({
        username,
        platform: selectedPlatform,
        theme_override: selectedTheme,
        layout: selectedLayout,
      }),
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      const msg = errData.detail || `HTTP ${response.status}`;
      throw new Error(response.status === 429 ? `Rate limited: ${msg}` : msg);
    }

    const data = await response.json();
    currentUsername  = data.username;
    currentCardUrl   = data.card_url ? `${BACKEND_URL}${data.card_url}` : '';

    if (data.card_url) {
      cardIframe.src = `${BACKEND_URL}${data.card_url}`;
    }

    stopLoadingSteps();
    skeleton.classList.remove('active');
    result.classList.add('active');

    // Record + display analytics
    recordAndShowViews(data.username);

  } catch (err) {
    console.error('Generate error:', err);
    stopLoadingSteps();
    skeleton.classList.remove('active');
    document.getElementById('error-title').textContent = 'Generation Failed';
    document.getElementById('error-message').textContent =
      err.name === 'AbortError'
        ? 'Request timed out after 2 minutes. Please try again.'
        : err.message.includes('not found')
          ? `The username "${username}" doesn't exist or is private.`
          : err.message.includes('fetch') || err.message.includes('Failed to fetch')
            ? 'Could not reach the backend server. Make sure it\'s running on port 8080.'
            : `Error: ${err.message}`;
    error.classList.add('active');
  } finally {
    generateBtn.disabled = false;
    generateBtn.innerHTML = '<span class="btn-icon">✨</span> Generate Card';
  }
}

// ── Analytics ─────────────────────────────────────────────────────────────────
async function recordAndShowViews(username) {
  try {
    const res = await fetch(`${BACKEND_URL}/analytics/view/${username}`, { method: 'POST', credentials: 'include' });
    const data = await res.json();
    const badge = document.getElementById('analytics-badge');
    const counter = document.getElementById('view-count-display');
    if (badge && counter) {
      counter.textContent = `👁️ ${data.views} view${data.views !== 1 ? 's' : ''}`;
      badge.style.display = 'flex';
    }
  } catch {}
}

// ── Copy card URL ─────────────────────────────────────────────────────────────
async function copyCardUrl() {
  if (!currentCardUrl) return;
  try {
    await navigator.clipboard.writeText(currentCardUrl);
  } catch {
    const ta = document.createElement('textarea');
    ta.value = currentCardUrl;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
  }
  shareBtn.innerHTML = '✅ Copied!';
  shareBtn.classList.add('copied');
  setTimeout(() => {
    shareBtn.innerHTML = '📋 Copy Link';
    shareBtn.classList.remove('copied');
  }, 2000);
}

// ── Open card ─────────────────────────────────────────────────────────────────
function openCard() {
  if (currentCardUrl) window.open(currentCardUrl, '_blank');
}

// ── Shared helper: fetch card HTML, sanitize CSS, render via Blob URL ─────────
async function fetchCardElement() {
  if (!currentCardUrl) throw new Error('No card URL available.');
  const res = await fetch(currentCardUrl);
  if (!res.ok) throw new Error(`Failed to fetch card: HTTP ${res.status}`);
  let html = await res.text();

  // Strip unsupported CSS functions so html2canvas doesn't choke
  html = html.replace(/color-mix\([^)]+\)/g, 'rgba(0,0,0,0.15)');
  // Remove backdrop-filter (not supported by html2canvas)
  html = html.replace(/backdrop-filter:[^;]+;/g, '');

  // Create a Blob URL — same-origin, so html2canvas can access it freely
  const blob = new Blob([html], { type: 'text/html' });
  const blobUrl = URL.createObjectURL(blob);

  return new Promise((resolve, reject) => {
    const iframe = document.createElement('iframe');
    iframe.style.cssText = 'position:fixed;left:-9999px;top:0;width:500px;height:800px;border:none;z-index:-1;';
    iframe.src = blobUrl;
    iframe.onload = () => {
      try {
        const cardEl = iframe.contentDocument.querySelector('.card') || iframe.contentDocument.body;
        // Give fonts a moment to load
        setTimeout(() => resolve({ cardEl, iframe, blobUrl }), 400);
      } catch (e) {
        reject(e);
      }
    };
    iframe.onerror = reject;
    document.body.appendChild(iframe);
  });
}

// ── PNG Export ────────────────────────────────────────────────────────────────
async function exportPNG() {
  const btn = document.getElementById('png-btn');
  btn.textContent = '⏳ Capturing...';
  btn.disabled = true;
  let iframe, blobUrl, cardEl;
  try {
    ({ cardEl, iframe, blobUrl } = await fetchCardElement());
    const canvas = await html2canvas(cardEl, {
      scale: 2,
      useCORS: true,
      allowTaint: true,
      backgroundColor: null,
      logging: false,
    });
    const link = document.createElement('a');
    link.download = `${currentUsername || 'devcard'}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
  } catch (e) {
    alert('PNG export failed: ' + e.message + '\n\nTry using "Open Card" and saving from there.');
  } finally {
    if (iframe) document.body.removeChild(iframe);
    if (blobUrl) URL.revokeObjectURL(blobUrl);
    btn.textContent = '⬇️ PNG';
    btn.disabled = false;
  }
}

// ── PDF Export ────────────────────────────────────────────────────────────────
async function exportPDF() {
  const btn = document.getElementById('pdf-btn');
  btn.textContent = '⏳ Generating...';
  btn.disabled = true;
  let iframe, blobUrl;
  try {
    ({ cardEl, iframe, blobUrl } = await fetchCardElement());
    const canvas = await html2canvas(cardEl, {
      scale: 2,
      useCORS: true,
      allowTaint: true,
      backgroundColor: null,
      logging: false,
    });
    const { jsPDF } = window.jspdf;
    const imgData = canvas.toDataURL('image/png');
    const pxToMm = 0.264583;
    const w = canvas.width * pxToMm;
    const h = canvas.height * pxToMm;
    const pdf = new jsPDF({ orientation: w > h ? 'l' : 'p', unit: 'mm', format: [w, h] });
    pdf.addImage(imgData, 'PNG', 0, 0, w, h);
    pdf.save(`${currentUsername || 'devcard'}.pdf`);
  } catch (e) {
    alert('PDF export failed: ' + e.message + '\n\nTry using "Open Card" and printing to PDF.');
  } finally {
    if (iframe) document.body.removeChild(iframe);
    if (blobUrl) URL.revokeObjectURL(blobUrl);
    btn.textContent = '📄 PDF';
    btn.disabled = false;
  }
}

// ── Reset UI ──────────────────────────────────────────────────────────────────
function resetUI() {
  error.classList.remove('active');
  result.classList.remove('active');
  skeleton.classList.remove('active');
  usernameInput.value = '';
  usernameInput.focus();
  const badge = document.getElementById('analytics-badge');
  if (badge) badge.style.display = 'none';
}
