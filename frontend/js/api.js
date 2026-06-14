/* ═══════════════════════════════════════════════
   WOMENSPACE — API Client (shared)
   Import di setiap halaman sebagai <script src="js/api.js">
   ═══════════════════════════════════════════════ */

const API_BASE =
  location.hostname === "localhost" || location.hostname === "127.0.0.1"
    ? "http://127.0.0.1:5000/api"
    : "https://womenspace.onrender.com/api";

const API_ORIGIN = API_BASE.replace("/api", "");

/* ── Token management ─────────────────────────── */
const Auth = {
  getToken : ()        => localStorage.getItem("ws_token"),
  setToken : (t)       => localStorage.setItem("ws_token", t),
  getUser  : ()        => JSON.parse(localStorage.getItem("ws_user") || "null"),
  setUser  : (u)       => localStorage.setItem("ws_user", JSON.stringify(u)),
  clear    : ()        => { localStorage.removeItem("ws_token"); localStorage.removeItem("ws_user"); },
  isLoggedIn: ()       => !!localStorage.getItem("ws_token"),
};

/* ── Core fetch wrapper ───────────────────────── */
async function api(path, options = {}) {
  const token   = Auth.getToken();
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (token)                        headers["Authorization"] = `Bearer ${token}`;
  if (options.body instanceof FormData) delete headers["Content-Type"];

  try {
    const res  = await fetch(API_BASE + path, { ...options, headers });
    const text = await res.text();
    let json   = {};
    try { json = JSON.parse(text); } catch (_) {}
    if (res.status === 401) {
      Auth.clear();
      if (!window.location.pathname.includes("login")) {
        window.location.href = "/login.html";
      }
    }
    return { ok: res.ok, status: res.status, data: json };
  } catch (err) {
    console.error(`[API] ${path}:`, err);
    throw err;
  }
}

/* ── Auth guard: redirect ke login kalau belum login ── */
function requireAuth() {
  if (!Auth.isLoggedIn()) {
    window.location.href = "/login.html";
    return false;
  }
  return true;
}

/* ── Redirect ke home kalau sudah login ───────── */
function redirectIfLoggedIn() {
  if (Auth.isLoggedIn()) {
    window.location.href = "/home.html";
  }
}

/* ── UI Helpers ───────────────────────────────── */
function toast(msg, type = "", duration = 3000) {
  let el = document.getElementById("toast");
  if (!el) {
    el = document.createElement("div");
    el.id = "toast";
    document.body.appendChild(el);
  }
  el.textContent = msg;
  el.className   = type ? `toast-${type}` : "";
  el.style.cssText = `
    position:fixed; bottom:28px; left:50%; transform:translateX(-50%);
    background:${type === "error" ? "#D94F4F" : type === "success" ? "#5BAD87" : "#2D2020"};
    color:#fff; padding:12px 24px; border-radius:9999px;
    font-size:.9rem; font-weight:500; z-index:9999;
    white-space:nowrap; animation:slideUp .3s ease;
    font-family:'DM Sans',sans-serif;
  `;
  el.classList.remove("hidden");
  clearTimeout(el._t);
  el._t = setTimeout(() => el.style.display = "none", duration);
}

function showError(id, msg) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = msg;
  el.classList.remove("hidden");
}
function clearError(id) {
  const el = document.getElementById(id);
  if (el) { el.textContent = ""; el.classList.add("hidden"); }
}

function formatTime(iso) {
  if (!iso) return "";
  // Backend simpan WIB, parse langsung tanpa konversi timezone
  const d    = new Date(iso.replace(" ", "T") + "+07:00");
  const now  = new Date();
  const diff = (now - d) / 1000;
  if (isNaN(diff) || diff < 0) return "baru saja";
  if (diff < 60)    return "baru saja";
  if (diff < 3600)  return `${Math.floor(diff / 60)} mnt lalu`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} jam lalu`;
  if (diff < 604800)return `${Math.floor(diff / 86400)} hr lalu`;
  return d.toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" });
}

function makeAvatar(url, fallback = "✿") {
  if (!url) return fallback;
  const src = url.startsWith("http") ? url : `${API_ORIGIN}${url}`;
  return `<img src="${src}" style="width:100%;height:100%;object-fit:cover;border-radius:50%" alt="avatar" onerror="this.parentElement.innerHTML='✿'"/>`;
}

function escHtml(str) {
  return String(str || "")
    .replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")
    .replace(/"/g,"&quot;").replace(/\n/g,"<br/>");
}

/* Highlight @mention di konten */
function renderContent(text) {
  return escHtml(text).replace(/@(\w+)/g,
    '<span class="mention" onclick="visitProfile(\'$1\')">@$1</span>');
}

function visitProfile(username) {
  api(`/users/by-username/${encodeURIComponent(username)}`).then(r => {
    if (r.ok && r.data.id) {
      window.location.href = `/profile.html?id=${r.data.id}`;
    } else {
      toast("Profil tidak ditemukan.", "error");
    }
  }).catch(() => toast("Gagal membuka profil.", "error"));
}

/* ── Navbar active state ─────────────────────── */
function setNavActive(page) {
  document.querySelectorAll(".nav-btn[data-page]").forEach(b => {
    b.classList.toggle("active", b.dataset.page === page);
  });
}

/* ── Render post card ────────────────────────── */
function renderPostCard(post, opts = {}) {
  const author  = post.author || {};
  const isAnon  = post.is_anonymous;
  const name    = isAnon ? "Anonim 🌸" : `@${escHtml(author.username || "unknown")}`;
  const media   = post.media_url ? renderMedia(post.media_url, post.media_type) : "";
  const pollHtml = post.poll ? renderPoll(post.poll) : "";
  const isOwn   = post.user_id === Auth.getUser()?.id;

  return `
  <div class="post-card ${post.pinned ? "post-pinned" : ""}" data-post-id="${post.id}">
    ${post.pinned ? `<div style="font-size:.75rem;color:var(--rose);font-weight:700;margin-bottom:8px">📌 Postingan Dipin</div>` : ""}
    <div class="post-header">
      <div class="avatar avatar-md" ${!isAnon ? `onclick="visitProfile('${escHtml(author.username||'')}')" style="cursor:pointer"` : ""}>
        ${isAnon ? "🌸" : makeAvatar(author.avatar_url)}
      </div>
      <div class="post-author" style="flex:1">
        <div class="post-author-name" ${!isAnon ? `onclick="visitProfile('${escHtml(author.username||'')}')"` : ""}>${name}</div>
        <div class="post-time">${formatTime(post.created_at)}</div>
      </div>
      ${isAnon ? '<span class="anon-label">Anonim</span>' : ""}
      ${isOwn ? `<button class="action-btn pin-btn" data-id="${post.id}" data-pinned="${post.pinned}" title="${post.pinned?"Lepas pin":"Pin postingan"}" style="margin-left:auto">${post.pinned ? "📌" : "📍"}</button>` : ""}
    </div>
    ${post.content ? `<div class="post-content">${renderContent(post.content)}</div>` : ""}
    ${media}
    ${pollHtml}
    <div class="post-actions">
      <button class="action-btn like-btn ${post.liked ? "liked" : ""}" data-id="${post.id}">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="${post.liked ? "currentColor" : "none"}" stroke="currentColor" stroke-width="2"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>
        <span class="like-count">${post.like_count || 0}</span>
      </button>
      <button class="action-btn reply-btn" data-id="${post.id}" data-content="${escHtml((post.content||"").substring(0,80))}">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
        ${post.reply_count || 0}
      </button>
      <button class="action-btn repost-btn" data-id="${post.id}">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 1l4 4-4 4"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><path d="M7 23l-4-4 4-4"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/></svg>
        ${post.repost_count || 0}
      </button>
      <button class="action-btn bookmark-btn ${post.bookmarked ? "bookmarked" : ""}" data-id="${post.id}">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="${post.bookmarked ? "currentColor" : "none"}" stroke="currentColor" stroke-width="2"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>
      </button>
    </div>
  </div>`;
}

/* ── Render Poll ─────────────────────────────── */
function renderPoll(poll) {
  const hasVoted    = !!poll.my_vote;
  const isEnded     = poll.is_ended;
  const showResults = hasVoted || isEnded;

  const optionsHtml = poll.options.map(opt => {
    const chosen = poll.my_vote === opt.id;
    if (showResults) {
      return `
        <div style="margin-bottom:9px">
          <div style="display:flex;justify-content:space-between;font-size:.85rem;margin-bottom:3px">
            <span style="font-weight:${chosen?"700":"400"};color:${chosen?"var(--rose)":"var(--text)"}">
              ${chosen ? "✓ " : ""}${escHtml(opt.label)}
            </span>
            <span style="color:var(--text-muted)">${opt.percent}% · ${opt.votes} suara</span>
          </div>
          <div style="height:7px;background:var(--cream-dark);border-radius:99px;overflow:hidden">
            <div style="height:100%;width:${opt.percent}%;background:${chosen?"var(--rose)":"var(--rose-light)"};border-radius:99px;transition:width .6s ease"></div>
          </div>
        </div>`;
    }
    return `
      <button class="poll-option-btn" data-poll-id="${poll.id}" data-option-id="${opt.id}"
        style="width:100%;padding:9px 14px;margin-bottom:7px;border-radius:var(--radius-sm);
               border:1.5px solid var(--border);background:var(--white);cursor:pointer;
               text-align:left;font-size:.88rem;font-family:inherit;font-weight:500;transition:all .18s"
        onmouseover="this.style.borderColor='var(--rose)';this.style.background='var(--rose-pale)'"
        onmouseout="this.style.borderColor='var(--border)';this.style.background='var(--white)'">
        ${escHtml(opt.label)}
      </button>`;
  }).join("");

  return `
  <div class="poll-widget" data-poll-id="${poll.id}"
    style="background:var(--blush);border:1.5px solid var(--border);
           border-radius:var(--radius-sm);padding:14px 16px;margin-bottom:14px">
    <div style="font-weight:700;font-size:.92rem;margin-bottom:12px">📊 ${escHtml(poll.question)}</div>
    <div class="poll-options">${optionsHtml}</div>
    <div style="display:flex;justify-content:space-between;margin-top:8px">
      <span style="font-size:.76rem;color:var(--text-muted)">${poll.total} suara total</span>
      <span style="font-size:.76rem;color:${isEnded?"var(--danger)":"var(--text-muted)"}">
        ${isEnded ? "⏰ Poll berakhir" : "⏱ Berakhir " + formatTime(poll.ends_at)}
      </span>
    </div>
  </div>`;
}

function renderMedia(url, type) {
   if (!url) return "";

  const full = url.startsWith("http") ? url : `${API_ORIGIN}${url}`;
  const mediaType = String(type || "").toLowerCase();

  if (mediaType.includes("image") || mediaType === "photo") {
    return `<div class="post-media"><img src="${full}" alt="media" loading="lazy" onerror="this.style.display='none'"/></div>`;
  }

  if (mediaType.includes("video")) {
    return `<div class="post-media"><video src="${full}" controls style="width:100%;border-radius:10px"></video></div>`;
  }

  if (mediaType.includes("audio")) {
    return `<div class="post-media"><audio src="${full}" controls style="width:100%"></audio></div>`;
  }

  return `<div class="post-media"><img src="${full}" alt="media" loading="lazy" onerror="this.style.display='none'"/></div>`;
}

/* ── Attach post interactions ────────────────── */
function attachPostActions(container) {
  // LIKE
  container.querySelectorAll(".like-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      const { ok, data } = await api(`/posts/${btn.dataset.id}/like`, { method: "POST" });
      if (!ok) return;
      btn.classList.toggle("liked", data.liked);
      btn.querySelector(".like-count").textContent = data.like_count;
      btn.querySelector("svg").setAttribute("fill", data.liked ? "currentColor" : "none");
    });
  });

  // REPLY
  container.querySelectorAll(".reply-btn").forEach(btn => {
    btn.addEventListener("click", () => openReplyModal(btn.dataset.id, btn.dataset.content));
  });

  // REPOST
  container.querySelectorAll(".repost-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      const { ok } = await api(`/posts/${btn.dataset.id}/repost`, { method: "POST" });
      if (ok) toast("🔁 Repost berhasil!", "success");
    });
  });

  // BOOKMARK
  container.querySelectorAll(".bookmark-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      const { ok, data } = await api(`/posts/${btn.dataset.id}/bookmark`, { method: "POST" });
      if (!ok) return;
      btn.classList.toggle("bookmarked", data.bookmarked);
      btn.querySelector("svg").setAttribute("fill", data.bookmarked ? "currentColor" : "none");
      toast(data.bookmarked ? "🔖 Disimpan!" : "Bookmark dihapus");
    });
  });

  // PIN
  container.querySelectorAll(".pin-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      const { ok, data } = await api(`/posts/${btn.dataset.id}/pin`, { method: "POST" });
      if (!ok) return;
      btn.dataset.pinned = data.pinned;
      btn.textContent    = data.pinned ? "📌" : "📍";
      btn.title          = data.pinned ? "Lepas pin" : "Pin postingan";
      toast(data.pinned ? "📌 Postingan di-pin!" : "Pin dilepas");
    });
  });

  // POLL VOTE
  container.querySelectorAll(".poll-option-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      const pollId    = btn.dataset.pollId;
      const optionId  = btn.dataset.optionId;
      const { ok, data } = await api(`/polls/${pollId}/vote`, {
        method: "POST",
        body  : JSON.stringify({ option_id: optionId })
      });
      if (!ok) { toast("Gagal vote.", "error"); return; }
      // Re-render poll widget dengan hasil terbaru
      const widget = container.querySelector(`.poll-widget[data-poll-id="${pollId}"]`);
      if (widget) {
        const pollData = {
          id       : pollId,
          question : widget.querySelector("div").textContent.trim().replace("📊 ",""),
          my_vote  : data.voted,
          total    : data.total,
          is_ended : false,
          options  : data.results
        };
        widget.outerHTML = renderPoll(pollData);
      }
    });
  });
}

/* ── Reply Modal ─────────────────────────────── */
let _replyTarget = null;
function openReplyModal(postId, content) {
  _replyTarget = postId;
  let modal = document.getElementById("reply-modal");
  if (!modal) {
    modal = document.createElement("div");
    modal.id        = "reply-modal";
    modal.className = "modal-overlay";
    modal.innerHTML = `
      <div class="modal">
        <div class="modal-header">
          <h3>Balas Postingan 💬</h3>
          <button class="modal-close" id="reply-modal-close">✕</button>
        </div>
        <div id="reply-original" style="background:var(--cream-dark);border-left:3px solid var(--rose-light);border-radius:var(--radius-sm);padding:10px 14px;margin-bottom:14px;font-size:.9rem;color:var(--text-muted);"></div>
        <textarea id="reply-text" placeholder="Tulis balasanmu..." rows="3"></textarea>
        <div id="reply-error" class="form-error hidden" style="margin-top:10px"></div>
        <button class="btn btn-primary btn-full" id="reply-submit" style="margin-top:14px">Kirim Balasan ✿</button>
      </div>`;
    document.body.appendChild(modal);
    document.getElementById("reply-modal-close").onclick = () => modal.classList.add("hidden");
    document.getElementById("reply-submit").onclick = submitReply;
  }
  document.getElementById("reply-original").innerHTML = content ? `<em>"${escHtml(content)}..."</em>` : "";
  document.getElementById("reply-text").value = "";
  clearError("reply-error");
  modal.classList.remove("hidden");
}

async function submitReply() {
  const text = document.getElementById("reply-text").value.trim();
  if (!text) { showError("reply-error", "Balasan tidak boleh kosong."); return; }
  const form = new FormData();
  form.append("content", text);
  const { ok, data } = await api(`/posts/${_replyTarget}/reply`, { method: "POST", body: form });
  if (!ok) { showError("reply-error", data.error || "Gagal."); return; }
  document.getElementById("reply-modal").classList.add("hidden");
  toast("💬 Balasan terkirim!", "success");
}

/* ── Unread polling ──────────────────────────── */
async function startUnreadPolling() {
  async function check() {
    try {
      const { ok, data } = await api("/notifications/unread-count");
      if (!ok) return;
      const nd = document.getElementById("nav-notif-dot");
      const dd = document.getElementById("nav-dm-dot");
      if (nd) nd.classList.toggle("hidden", (data.notifications||0) === 0);
      if (dd) dd.classList.toggle("hidden", (data.messages||0) === 0);
    } catch {}
  }
  check();
  setInterval(check, 20000);
}


/* Navbar HTML (shared) */
function renderNavbar(activePage) {
  const user   = Auth.getUser();
  const isMore = ["profile","bookmarks","anonim","konsultasi"].includes(activePage);

  const nav = `
  <nav class="navbar">
    <div class="nav-logo">
      <div class="nav-logo-mark">✿</div>
      <div class="nav-logo-text">Womenspace</div>
    </div>

    <!-- Desktop: semua link di sidebar -->
    <div class="nav-links nav-desktop">
      <a href="/home.html" class="nav-btn ${activePage==="home"?"active":""}">
        <svg viewBox="0 0 24 24"><path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z"/></svg><span>Beranda</span>
      </a>
      <a href="/search.html" class="nav-btn ${activePage==="search"?"active":""}">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg><span>Jelajahi</span>
      </a>
      <a href="/notifications.html" class="nav-btn ${activePage==="notifications"?"active":""}" style="position:relative">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
        <span>Notifikasi</span><div class="nav-notif-dot hidden" id="nav-notif-dot-d"></div>
      </a>
      <a href="/dm.html" class="nav-btn ${activePage==="dm"?"active":""}" style="position:relative">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
        <span>Pesan</span><div class="nav-notif-dot hidden" id="nav-dm-dot-d"></div>
      </a>
      <a href="/konsultasi.html" class="nav-btn ${activePage==="konsultasi"?"active":""}">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 13a19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 3.6 2h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L7.91 9.91a16 16 0 0 0 6.18 6.18l1.27-.91a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg><span>Konsultasi</span>
      </a>
      <a href="/bookmarks.html" class="nav-btn ${activePage==="bookmarks"?"active":""}">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg><span>Tersimpan</span>
      </a>
      <a href="/anonim.html" class="nav-btn ${activePage==="anonim"?"active":""}">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg><span>Anonim</span>
      </a>
      <a href="/profile.html" class="nav-btn ${activePage==="profile"?"active":""}">
        <svg viewBox="0 0 24 24"><path d="M12 12c2.7 0 4.8-2.1 4.8-4.8S14.7 2.4 12 2.4 7.2 4.5 7.2 7.2 9.3 12 12 12zm0 2.4c-3.2 0-9.6 1.6-9.6 4.8v2.4h19.2v-2.4c0-3.2-6.4-4.8-9.6-4.8z"/></svg><span>Profil</span>
      </a>
    </div>

    <!-- Mobile: hanya 5 item -->
    <div class="nav-links nav-mobile">
      <a href="/home.html" class="nav-btn ${activePage==="home"?"active":""}">
        <svg viewBox="0 0 24 24"><path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z"/></svg><span>Home</span>
      </a>
      <a href="/search.html" class="nav-btn ${activePage==="search"?"active":""}">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg><span>Explore</span>
      </a>
      <a href="/notifications.html" class="nav-btn ${activePage==="notifications"?"active":""}" style="position:relative">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
        <span>Notif</span><div class="nav-notif-dot hidden" id="nav-notif-dot"></div>
      </a>
      <a href="/dm.html" class="nav-btn ${activePage==="dm"?"active":""}" style="position:relative">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
        <span>Pesan</span><div class="nav-notif-dot hidden" id="nav-dm-dot"></div>
      </a>
      <button class="nav-btn ${isMore?"active":""}" onclick="toggleMoreMenu()">
        <svg viewBox="0 0 24 24" fill="currentColor"><circle cx="5" cy="12" r="2"/><circle cx="12" cy="12" r="2"/><circle cx="19" cy="12" r="2"/></svg>
        <span>Lainnya</span>
      </button>
    </div>

    <div class="nav-bottom">
      <div class="nav-user" onclick="window.location.href='/profile.html'">
        <div class="avatar avatar-sm">${makeAvatar(user?.avatar_url)}</div>
        <div style="flex:1;min-width:0"><div class="nav-user-name">@${user?.username||"..."}</div></div>
      </div>
      <a href="/login.html" class="nav-btn" onclick="Auth.clear();return true;" style="color:var(--danger);margin-top:4px">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
        <span>Keluar</span>
      </a>
    </div>
  </nav>

  <!-- More Menu sheet (mobile) -->
  <div id="more-menu" class="more-overlay hidden" onclick="toggleMoreMenu()">
    <div class="more-sheet" onclick="event.stopPropagation()">
      <div class="more-handle"></div>
      <p class="more-title">Menu Lainnya</p>
      <div class="more-grid">
        <a href="/profile.html" class="more-item ${activePage==="profile"?"more-active":""}">
          <div class="more-icon">👤</div><span>Profil Saya</span>
        </a>
        <a href="/konsultasi.html" class="more-item ${activePage==="konsultasi"?"more-active":""}">
          <div class="more-icon">🧠</div><span>Konsultasi</span>
        </a>
        <a href="/bookmarks.html" class="more-item ${activePage==="bookmarks"?"more-active":""}">
          <div class="more-icon">🔖</div><span>Tersimpan</span>
        </a>
        <a href="/anonim.html" class="more-item ${activePage==="anonim"?"more-active":""}">
          <div class="more-icon">🎭</div><span>Anonim</span>
        </a>
        <a href="/login.html" class="more-item" onclick="Auth.clear();return true;" style="color:var(--danger)">
          <div class="more-icon">🚪</div><span>Keluar</span>
        </a>
      </div>
    </div>
  </div>`;

  setTimeout(startUnreadPolling, 500);
  return nav;
}

function toggleMoreMenu() {
  const el = document.getElementById("more-menu");
  if (el) el.classList.toggle("hidden");
}
