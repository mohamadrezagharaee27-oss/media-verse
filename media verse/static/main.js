/* ===== THEME ===== */
function applyTheme(theme) {
  document.body.classList.toggle('light-theme', theme === 'light');
}

/* ===== DROPDOWN ===== */
document.addEventListener('click', (e) => {
  const toggle = e.target.closest('[data-dropdown]');
  const menus = document.querySelectorAll('.dropdown-menu');

  menus.forEach(m => {
    if (!toggle || !m.closest('.dropdown').contains(toggle)) {
      m.classList.remove('show');
    }
  });

  if (toggle) {
    const menu = toggle.closest('.dropdown').querySelector('.dropdown-menu');
    if (menu) menu.classList.toggle('show');
  }
});

/* ===== FLASH AUTO-DISMISS ===== */
document.querySelectorAll('.alert').forEach(el => {
  setTimeout(() => {
    el.style.transition = 'opacity 0.4s';
    el.style.opacity = '0';
    setTimeout(() => el.remove(), 400);
  }, 4000);
});

/* ===== CSRF TOKEN HELPER ===== */
function getCSRF() {
  const meta = document.querySelector('meta[name="csrf-token"]');
  return meta ? meta.content : '';
}

/* ===== LIKE BUTTON ===== */
function initLike() {
  const btn = document.getElementById('like-btn');
  if (!btn) return;

  btn.addEventListener('click', async () => {
    const uploadId = btn.dataset.uploadId;
    try {
      const res = await fetch(`/api/like/${uploadId}`, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCSRF(), 'Content-Type': 'application/json' }
      });
      if (res.status === 401) { window.location = '/auth/login'; return; }
      const data = await res.json();
      btn.classList.toggle('liked', data.liked);
      const countEl = btn.querySelector('.like-count');
      if (countEl) countEl.textContent = formatNum(data.count);
    } catch (err) { console.error(err); }
  });
}

/* ===== COMMENTS ===== */
function initComments() {
  const form = document.getElementById('comment-form');
  const list = document.getElementById('comment-list');
  const countEl = document.getElementById('comment-count');
  if (!form) return;

  const uploadId = form.dataset.uploadId;
  const textarea = form.querySelector('.comment-input');
  const submitBtn = form.querySelector('.comment-submit');
  const cancelBtn = form.querySelector('.comment-cancel');

  // Expand on focus
  textarea.addEventListener('focus', () => {
    textarea.rows = 3;
    submitBtn.classList.remove('hidden');
    cancelBtn.classList.remove('hidden');
  });

  cancelBtn.addEventListener('click', () => {
    textarea.value = '';
    textarea.rows = 1;
    submitBtn.classList.add('hidden');
    cancelBtn.classList.add('hidden');
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const content = textarea.value.trim();
    if (!content) return;
    submitBtn.disabled = true;

    try {
      const res = await fetch(`/api/comment/${uploadId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCSRF()
        },
        body: JSON.stringify({ content })
      });
      if (res.status === 401) { window.location = '/auth/login'; return; }
      const data = await res.json();
      if (data.error) { alert(data.error); return; }

      // Prepend comment
      const el = createCommentEl(data);
      list.insertBefore(el, list.firstChild);
      textarea.value = ''; textarea.rows = 1;
      submitBtn.classList.add('hidden');
      cancelBtn.classList.add('hidden');
      if (countEl) countEl.textContent = formatNum(data.count);
    } catch (err) { console.error(err); }
    finally { submitBtn.disabled = false; }
  });

  // Delete / Edit via event delegation
  list.addEventListener('click', async (e) => {
    const delBtn = e.target.closest('[data-delete-comment]');
    const editBtn = e.target.closest('[data-edit-comment]');

    if (delBtn) {
      if (!confirm('Delete this comment?')) return;
      const id = delBtn.dataset.deleteComment;
      const res = await fetch(`/api/comment/${id}`, {
        method: 'DELETE', headers: { 'X-CSRFToken': getCSRF() }
      });
      const data = await res.json();
      if (data.success) {
        delBtn.closest('.comment-item').remove();
        if (countEl) countEl.textContent = formatNum(data.count);
      }
    }

    if (editBtn) {
      const id = editBtn.dataset.editComment;
      const item = editBtn.closest('.comment-item');
      const textEl = item.querySelector('.comment-text');
      const current = textEl.textContent.trim();
      const newText = prompt('Edit comment:', current);
      if (!newText || newText.trim() === current) return;

      const res = await fetch(`/api/comment/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRF() },
        body: JSON.stringify({ content: newText.trim() })
      });
      const data = await res.json();
      if (data.success) textEl.textContent = data.content;
    }
  });
}

function createCommentEl(data) {
  const div = document.createElement('div');
  div.className = 'comment-item';
  div.dataset.commentId = data.id;
  div.innerHTML = `
    <img src="${data.author_avatar}" alt="${data.author_name}">
    <div class="comment-body">
      <div class="comment-author">
        <a href="/profile/${data.author_username}">${data.author_name}</a>
        <span>just now</span>
      </div>
      <p class="comment-text">${escapeHtml(data.content)}</p>
      <div class="comment-btns">
        <button class="comment-btn" data-edit-comment="${data.id}">Edit</button>
        <button class="comment-btn danger" data-delete-comment="${data.id}">Delete</button>
      </div>
    </div>
  `;
  return div;
}

/* ===== UPLOAD DROPZONE ===== */
function initUploadDropzone() {
  const zone = document.getElementById('dropzone');
  const input = document.getElementById('file-input');
  const label = document.getElementById('file-label');
  if (!zone || !input) return;

  zone.addEventListener('click', () => input.click());
  zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('dragging'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('dragging'));
  zone.addEventListener('drop', (e) => {
    e.preventDefault(); zone.classList.remove('dragging');
    if (e.dataTransfer.files.length) {
      input.files = e.dataTransfer.files;
      updateFileLabel(input.files[0]);
    }
  });
  input.addEventListener('change', () => {
    if (input.files.length) updateFileLabel(input.files[0]);
  });

  function updateFileLabel(file) {
    if (label) {
      label.textContent = `${file.name} (${formatBytes(file.size)})`;
      label.parentElement.style.display = 'flex';
    }
  }
}

/* ===== NOTIFICATIONS ===== */
async function loadNotifCount() {
  const badge = document.getElementById('notif-badge');
  if (!badge) return;
  try {
    const res = await fetch('/api/notifications/count');
    if (!res.ok) return;
    const data = await res.json();
    if (data.count > 0) {
      badge.textContent = data.count > 9 ? '9+' : data.count;
      badge.style.display = 'flex';
    } else {
      badge.style.display = 'none';
    }
  } catch {}
}

async function markNotifsRead() {
  await fetch('/api/notifications/read', {
    method: 'POST', headers: { 'X-CSRFToken': getCSRF() }
  });
  const badge = document.getElementById('notif-badge');
  if (badge) badge.style.display = 'none';
}

/* ===== SETTINGS TABS ===== */
function initSettingsTabs() {
  const navItems = document.querySelectorAll('.settings-nav-item');
  const tabs = document.querySelectorAll('.settings-tab');
  navItems.forEach(item => {
    item.addEventListener('click', () => {
      const target = item.dataset.tab;
      navItems.forEach(n => n.classList.remove('active'));
      tabs.forEach(t => t.classList.remove('active'));
      item.classList.add('active');
      document.getElementById(`tab-${target}`)?.classList.add('active');
    });
  });
}

/* ===== HELPERS ===== */
function formatNum(n) {
  if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M';
  if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K';
  return String(n);
}

function formatBytes(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / 1048576).toFixed(1) + ' MB';
}

function escapeHtml(str) {
  const d = document.createElement('div');
  d.appendChild(document.createTextNode(str));
  return d.innerHTML;
}

/* ===== INIT ===== */
document.addEventListener('DOMContentLoaded', () => {
  initLike();
  initComments();
  initUploadDropzone();
  initSettingsTabs();
  if (document.body.dataset.loggedIn === 'true') {
    loadNotifCount();
    setInterval(loadNotifCount, 30000);
  }
});
