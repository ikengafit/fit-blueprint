/* ─── iKengaFit Pre-Fit Blueprint — Form Logic ─────────────── */

// ─── BACKEND URL ─────────────────────────────────────────────
// When running locally, the backend is on the same host (relative path works).
// When the form is hosted as a static site (pplx.app), we must point to the
// deployed backend explicitly.  Update PRODUCTION_BACKEND_URL when you deploy
// the server to Render / Railway / any public host.
const PRODUCTION_BACKEND_URL = 'https://ikengafit-blueprint.onrender.com';
const BACKEND_URL = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
  ? ''   // relative path — backend serves the form locally
  : PRODUCTION_BACKEND_URL;

const TOTAL_SECTIONS = 4;
let currentSection = 1;

// ─── SECTION NAVIGATION ──────────────────────────────────────
function goToSection(n) {
  // Validate before going forward
  if (n > currentSection) {
    if (!validateSection(currentSection)) return;
  }

  const current = document.querySelector(`.form-section[data-section="${currentSection}"]`);
  const next    = document.querySelector(`.form-section[data-section="${n}"]`);
  if (!next) return;

  current.classList.remove('active');
  next.classList.add('active');
  currentSection = n;

  updateProgress(n);
  window.scrollTo({ top: document.querySelector('.progress-bar-wrap').offsetTop - 70, behavior: 'smooth' });
}

function updateProgress(section) {
  const pct = ((section - 1) / (TOTAL_SECTIONS - 1)) * 100;
  document.getElementById('progressBar').style.width = pct + '%';
  document.getElementById('progressLabel').textContent = `Section ${section} of ${TOTAL_SECTIONS}`;
}

// ─── VALIDATION ───────────────────────────────────────────────
function validateSection(section) {
  const s = document.querySelector(`.form-section[data-section="${section}"]`);
  const required = s.querySelectorAll('[required]');
  let valid = true;

  required.forEach(el => {
    clearError(el);
    if (el.type === 'radio') {
      // Radio groups — check if any in the group is checked
      const name = el.name;
      const group = s.querySelectorAll(`[name="${name}"]`);
      const checked = Array.from(group).some(r => r.checked);
      if (!checked) {
        showError(el, 'Please select an option.');
        valid = false;
      }
      return;
    }
    if (el.type === 'checkbox' && !el.checked) {
      showError(el, 'Please check this box to continue.');
      valid = false;
      return;
    }
    if (!el.value.trim()) {
      showError(el, 'This field is required.');
      valid = false;
    } else if (el.type === 'email' && !el.value.includes('@')) {
      showError(el, 'Please enter a valid email address.');
      valid = false;
    }
  });

  if (!valid) {
    // Scroll to first error
    const firstErr = s.querySelector('.error');
    if (firstErr) firstErr.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
  return valid;
}

function showError(el, msg) {
  el.classList.add('error');
  // Find or create error message element
  const container = el.closest('.field, .radio-group, .consent-field, .pkg-cards') || el.parentElement;
  let errEl = container.querySelector('.error-msg');
  if (!errEl) {
    errEl = document.createElement('p');
    errEl.className = 'error-msg';
    container.appendChild(errEl);
  }
  errEl.textContent = msg;
  errEl.classList.add('visible');
}

function clearError(el) {
  el.classList.remove('error');
  const container = el.closest('.field, .radio-group, .consent-field, .pkg-cards') || el.parentElement;
  const errEl = container && container.querySelector('.error-msg');
  if (errEl) { errEl.textContent = ''; errEl.classList.remove('visible'); }
}

// Clear errors on input
document.querySelectorAll('input, select, textarea').forEach(el => {
  el.addEventListener('input', () => clearError(el));
  el.addEventListener('change', () => clearError(el));
});

// ─── FORM SUBMIT ─────────────────────────────────────────────
document.getElementById('blueprintForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  if (!validateSection(4)) return;

  const submitBtn = document.getElementById('submitBtn');
  submitBtn.classList.add('loading');
  submitBtn.disabled = true;

  // Collect all form data
  const form = e.target;
  const formData = new FormData(form);

  // Handle multi-value checkboxes (focus areas, barriers)
  const focusAreas = Array.from(form.querySelectorAll('[name="focusAreas"]:checked')).map(el => el.value).join(', ') || '';
  const barriers = Array.from(form.querySelectorAll('[name="barriers"]:checked')).map(el => el.value).join(', ') || '';

  const payload = {};
  formData.forEach((val, key) => {
    if (key !== 'focusAreas' && key !== 'barriers') payload[key] = val;
  });
  payload.focusAreas = focusAreas;
  payload.barriers   = barriers;

  try {
    const res = await fetch(BACKEND_URL + '/api/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!res.ok) throw new Error(`Server error ${res.status}`);
    const data = await res.json();

    if (data.success) {
      showSuccess(data);
    } else {
      throw new Error(data.error || 'Unknown error');
    }
  } catch (err) {
    console.error('Submission error:', err);
    submitBtn.classList.remove('loading');
    submitBtn.disabled = false;
    alert('Something went wrong generating your proposal. Please try again.\n\n' + err.message);
  }
});

// ─── SUCCESS STATE ────────────────────────────────────────────
function showSuccess(data) {
  document.getElementById('formMain').style.display = 'none';
  document.getElementById('progressWrap').style.display = 'none';

  const successScreen = document.getElementById('successScreen');
  successScreen.hidden = false;

  // Personalize with client name
  const firstName = (data.clientName || 'there').split(' ')[0];
  document.getElementById('successName').textContent = firstName + '!';

  // Set download link — use a direct server URL
  const downloadLink = document.getElementById('downloadLink');
  const serverBase = window.location.origin;
  downloadLink.href = serverBase + data.downloadUrl;
  downloadLink.setAttribute('download', data.fileName || 'iKengaFit_Blueprint.pptx');

  // Scroll to success
  successScreen.scrollIntoView({ behavior: 'smooth', block: 'start' });

  // Confetti-lite effect
  spawnConfetti();
}

// ─── MINI CONFETTI ────────────────────────────────────────────
function spawnConfetti() {
  const colors = ['#028381', '#8A2C0E', '#F5F1EB', '#FFFFFF', '#01605F'];
  for (let i = 0; i < 60; i++) {
    setTimeout(() => {
      const dot = document.createElement('div');
      dot.style.cssText = `
        position:fixed;top:${Math.random()*20}%;left:${10+Math.random()*80}%;
        width:${4+Math.random()*6}px;height:${4+Math.random()*6}px;
        background:${colors[Math.floor(Math.random()*colors.length)]};
        border-radius:${Math.random()>0.5?'50%':'2px'};
        pointer-events:none;z-index:9999;opacity:1;
        transition:transform 1.8s ease, opacity 1.8s ease;
        transform:translate(${(Math.random()-0.5)*40}px,0);
      `;
      document.body.appendChild(dot);
      requestAnimationFrame(() => {
        dot.style.transform = `translate(${(Math.random()-0.5)*80}px, ${150+Math.random()*200}px)`;
        dot.style.opacity = '0';
      });
      setTimeout(() => dot.remove(), 2200);
    }, i * 20);
  }
}

// ─── INITIALIZE ──────────────────────────────────────────────
updateProgress(1);
