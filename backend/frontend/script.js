    // ── Configuration ──────────────────────────────────────────────
    const BACKEND_URL = window.location.origin;

    // ── DOM refs ───────────────────────────────────────────────────
    const usernameInput = document.getElementById('username-input');
    const generateBtn   = document.getElementById('generate-btn');
    const skeleton      = document.getElementById('skeleton');
    const result        = document.getElementById('result');
    const error         = document.getElementById('error');
    const cardIframe    = document.getElementById('card-iframe');
    const loadingText   = document.getElementById('loading-text');
    const shareBtn      = document.getElementById('share-btn');

    let currentCardUrl = '';

    // ── Enter key support ──────────────────────────────────────────
    usernameInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') generateCard();
    });

    // ── Loading step messages ──────────────────────────────────────
    const loadingSteps = [
      '🔍 Scraping GitHub profile...',
      '🤖 Analyzing with Gemini AI...',
      '🎨 Generating themed card...',
      '💾 Saving your dev card...',
      '⏳ Almost there, AI is thinking...',
      '⏳ Still working, this can take up to 60s...',
    ];

    let stepIndex = 0;
    let stepInterval = null;

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

    // ── Main generate function ─────────────────────────────────────
    async function generateCard() {
      const username = usernameInput.value.trim();
      if (!username) {
        usernameInput.focus();
        usernameInput.style.borderColor = 'var(--red)';
        setTimeout(() => usernameInput.style.borderColor = '', 1500);
        return;
      }

      // Show loading state
      generateBtn.disabled = true;
      generateBtn.innerHTML = '<div class="loading-spinner" style="width:14px;height:14px;border-width:2px;"></div> Generating...';
      skeleton.classList.add('active');
      result.classList.remove('active');
      error.classList.remove('active');
      startLoadingSteps();

      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 120000); // 2 min timeout

        const response = await fetch(`${BACKEND_URL}/generate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username }),
          signal: controller.signal,
        });
        clearTimeout(timeoutId);

        if (!response.ok) {
          const errData = await response.json().catch(() => ({}));
          const msg = errData.detail || `HTTP ${response.status}`;
          throw new Error(response.status === 429 ? `Rate limited: ${msg}` : msg);
        }

        const data = await response.json();

        // Store the card URL for sharing
        currentCardUrl = data.card_url
          ? `${BACKEND_URL}${data.card_url}`
          : '';

        // Load the card in the iframe
        if (data.card_url) {
          cardIframe.src = `${BACKEND_URL}${data.card_url}`;
        }

        // Show result
        stopLoadingSteps();
        skeleton.classList.remove('active');
        result.classList.add('active');

      } catch (err) {
        console.error('Generate error:', err);
        stopLoadingSteps();
        skeleton.classList.remove('active');

        // Show error
        document.getElementById('error-title').textContent = 'Generation Failed';
        document.getElementById('error-message').textContent =
          err.name === 'AbortError'
            ? 'Request timed out after 2 minutes. The backend may be overloaded — please try again.'
            : err.message.includes('not found')
              ? `The username "${username}" doesn't exist or is private. Check the spelling and try again.`
              : err.message.includes('fetch') || err.message.includes('Failed to fetch')
                ? 'Could not reach the backend server. Make sure it\'s running on port 8080.'
                : `Error: ${err.message}`;
        error.classList.add('active');

      } finally {
        generateBtn.disabled = false;
        generateBtn.innerHTML = '<span class="btn-icon">✨</span> Generate Card';
      }
    }

    // ── Copy card URL ──────────────────────────────────────────────
    async function copyCardUrl() {
      if (!currentCardUrl) return;

      try {
        await navigator.clipboard.writeText(currentCardUrl);
        shareBtn.innerHTML = '✅ Copied!';
        shareBtn.classList.add('copied');
        setTimeout(() => {
          shareBtn.innerHTML = '📋 Copy Link';
          shareBtn.classList.remove('copied');
        }, 2000);
      } catch {
        // Fallback for HTTP contexts
        const ta = document.createElement('textarea');
        ta.value = currentCardUrl;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        shareBtn.innerHTML = '✅ Copied!';
        shareBtn.classList.add('copied');
        setTimeout(() => {
          shareBtn.innerHTML = '📋 Copy Link';
          shareBtn.classList.remove('copied');
        }, 2000);
      }
    }

    // ── Open card in new tab ───────────────────────────────────────
    function openCard() {
      if (currentCardUrl) window.open(currentCardUrl, '_blank');
    }

    // ── Reset UI ───────────────────────────────────────────────────
    function resetUI() {
      error.classList.remove('active');
      result.classList.remove('active');
      skeleton.classList.remove('active');
      usernameInput.value = '';
      usernameInput.focus();
    }
