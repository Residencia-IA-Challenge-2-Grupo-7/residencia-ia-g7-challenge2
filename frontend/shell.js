let _toastTimer = null;

function showToast(msg) {
  const el = document.getElementById('toast');
  if (!el) return;
  el.textContent = msg;
  el.classList.add('show');
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => el.classList.remove('show'), 2700);
}

function toggleSingleAccordion(btnId, bodyId, pillId) {
  const btn = document.getElementById(btnId);
  const body = document.getElementById(bodyId);
  const pill = document.getElementById(pillId);
  const next = btn.getAttribute('aria-expanded') !== 'true';
  btn.setAttribute('aria-expanded', String(next));
  body.classList.toggle('open', next);
  pill.textContent = next ? 'Fechar aba ▴' : 'Abrir aba ▾';
}
