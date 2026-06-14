/* ═══════════════════════════════════════════════════
   WOMENSPACE — Frontend JS (Vanilla)
   Alur Register: Step1 (data akun) → Step2 (verifikasi wajah) → masuk
   ═══════════════════════════════════════════════════ */

const API_BASE =
  location.hostname === "localhost" || location.hostname === "127.0.0.1"
      ? "http://127.0.0.1:5000/api"
      : "https://womenspace.onrender.com/api";

const API_ORIGIN = API_BASE.replace("/api", "");

/* ─────────────────────────────────────────────────
   STATE
───────────────────────────────────────────────── */
let TOKEN        = localStorage.getItem("ws_token") || null;
let CURRENT_USER = JSON.parse(localStorage.getItem("ws_user") || "null");
let CURRENT_FEED = "fyp";
let REPLY_TARGET = null;

/* ─────────────────────────────────────────────────
   HELPERS
───────────────────────────────────────────────── */
async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (TOKEN) headers["Authorization"] = `Bearer ${TOKEN}`;
  if (options.body instanceof FormData) delete headers["Content-Type"];

  try {
    const res  = await fetch(API_BASE + path, { ...options, headers });
    const text = await res.text();                      // baca sebagai text dulu
    let json = {};
    try { json = JSON.parse(text); } catch (_) {
      console.warn(`[API] Non-JSON response from ${path}:`, text.slice(0, 200));
    }
    console.log(`[API] ${options.method || "GET"} ${path} → ${res.status}`, json);
    return { ok: res.ok, status: res.status, data: json };
  } catch (err) {
    console.error(`[API] Network error on ${path}:`, err);
    throw err;
  }
}

function toast(msg, duration = 3000) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.classList.remove("hidden");
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.add("hidden"), duration);
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
  const d    = new Date(iso);
  const diff = (Date.now() - d) / 1000;
  if (diff < 60)    return "baru saja";
  if (diff < 3600)  return `${Math.floor(diff / 60)} menit lalu`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} jam lalu`;
  return d.toLocaleDateString("id-ID", { day: "numeric", month: "short" });
}

function makeAvatar(avatarUrl, fallback = "✿") {
  if (avatarUrl)
    return `<img src="${API_BASE.replace("/api", "")}${avatarUrl}" alt="avatar"
             style="width:100%;height:100%;object-fit:cover;border-radius:50%"/>`;
  return fallback;
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/\n/g, "<br/>");
}

/* ─────────────────────────────────────────────────
   SCREEN / PAGE SWITCHER
───────────────────────────────────────────────── */
function showScreen(id) {
  document.querySelectorAll(".screen").forEach(s => s.classList.remove("active"));
  document.getElementById(id).classList.add("active");
}

function showPage(id) {
  document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
  document.getElementById(id).classList.add("active");
  document.querySelectorAll(".nav-btn[data-page]").forEach(b => {
    b.classList.toggle("active", `page-${b.dataset.page}` === id);
  });
}

/* ═══════════════════════════════════════════════
   AUTH TABS (Login ↔ Daftar)
═══════════════════════════════════════════════ */
document.querySelectorAll(".auth-tab").forEach(tab => {
  tab.addEventListener("click", () => {
    const which = tab.dataset.tab;
    document.querySelectorAll(".auth-tab").forEach(t => t.classList.remove("active"));
    tab.classList.add("active");
    document.querySelector(".auth-tab-indicator")
      .classList.toggle("right", which === "register");
    document.querySelectorAll(".form-panel").forEach(p => p.classList.remove("active"));
    document.getElementById(`form-${which}`).classList.add("active");
  });
});

/* ═══════════════════════════════════════════════
   REGISTER — STEP 1: Isi Data Akun Dulu
═══════════════════════════════════════════════ */
document.getElementById("btn-next-step").addEventListener("click", () => {
  clearError("reg-step1-error");
  const username = document.getElementById("reg-username").value.trim();
  const email    = document.getElementById("reg-email").value.trim();
  const password = document.getElementById("reg-password").value;

  if (!username)                     { showError("reg-step1-error", "Username wajib diisi."); return; }
  if (!email || !email.includes("@")){ showError("reg-step1-error", "Email tidak valid."); return; }
  if (password.length < 8)           { showError("reg-step1-error", "Password minimal 8 karakter."); return; }

  // Pindah ke Step 2
  document.getElementById("reg-step-1").classList.remove("active");
  document.getElementById("reg-step-2").classList.add("active");
  document.getElementById("dot-1").classList.remove("active");
  document.getElementById("dot-1").classList.add("done");
  document.getElementById("dot-2").classList.add("active");

  // Reset state foto
  document.getElementById("face-input").value = "";
  document.getElementById("face-preview-wrap").classList.add("hidden");
  document.getElementById("face-upload-area").classList.remove("hidden");
  document.getElementById("face-status").className    = "face-status";
  document.getElementById("face-status").textContent  = "";
  clearError("reg-step2-error");
});

/* Kembali ke Step 1 */
document.getElementById("btn-back-step").addEventListener("click", () => {
  document.getElementById("reg-step-2").classList.remove("active");
  document.getElementById("reg-step-1").classList.add("active");
  document.getElementById("dot-2").classList.remove("active");
  document.getElementById("dot-1").classList.remove("done");
  document.getElementById("dot-1").classList.add("active");
});

/* Preview foto setelah dipilih */
document.getElementById("face-input").addEventListener("change", () => {
  const file = document.getElementById("face-input").files[0];
  if (!file) return;
  document.getElementById("face-preview").src = URL.createObjectURL(file);
  document.getElementById("face-preview-wrap").classList.remove("hidden");
  document.getElementById("face-upload-area").classList.add("hidden");
  document.getElementById("face-status").className   = "face-status";
  document.getElementById("face-status").textContent = "";
  clearError("reg-step2-error");
});

/* ═══════════════════════════════════════════════
   REGISTER — STEP 2: Verifikasi Wajah + Submit
═══════════════════════════════════════════════ */
document.getElementById("btn-verify-face").addEventListener("click", async () => {
  clearError("reg-step2-error");

  const file = document.getElementById("face-input").files[0];
  if (!file) {
    showError("reg-step2-error", "Pilih foto wajahmu terlebih dahulu.");
    return;
  }

  // Ambil data dari step 1
  const username = document.getElementById("reg-username").value.trim();
  const email    = document.getElementById("reg-email").value.trim();
  const password = document.getElementById("reg-password").value;

  // Validasi ulang kalau user skip step 1 entah gimana
  if (!username || !email || password.length < 8) {
    showError("reg-step2-error", "Data akun tidak lengkap. Kembali ke langkah 1.");
    return;
  }

  const statusEl = document.getElementById("face-status");
  const btn      = document.getElementById("btn-verify-face");
  const backBtn  = document.getElementById("btn-back-step");

  function setStatus(type, msg) {
    statusEl.className   = `face-status ${type}`;
    statusEl.textContent = msg;
    statusEl.style.display = "block";
  }

  function resetBtn() {
    btn.disabled     = false;
    backBtn.disabled = false;
    btn.textContent  = "Verifikasi & Daftar 🌸";
  }

  // ── STEP 2A: Verifikasi wajah ────────────────
  btn.disabled = true; backBtn.disabled = true;
  btn.textContent = "⏳ Memverifikasi...";
  setStatus("loading", "⏳ Menganalisis wajah dengan AI... mohon tunggu");

  let vRes;
  try {
    const faceForm = new FormData();
    faceForm.append("face_photo", file);
    vRes = await api("/auth/verify-face", { method: "POST", body: faceForm });
    console.log("[REGISTER] verify-face response:", vRes);
  } catch (err) {
    console.error("[REGISTER] verify-face network error:", err);
    setStatus("error", "❌ Tidak bisa terhubung ke server. Pastikan backend jalan di port 5000.");
    resetBtn(); return;
  }

  if (!vRes.ok || !vRes.data.allowed) {
    setStatus("error", "❌ " + (vRes.data?.message || "Verifikasi wajah gagal."));
    resetBtn();
    btn.textContent = "🔄 Coba Lagi";
    return;
  }

  // Verifikasi wajah OK
  setStatus("success", "✅ Wajah terverifikasi sebagai perempuan! Membuat akun...");
  btn.textContent = "⏳ Membuat akun...";

  // ── STEP 2B: Register akun ───────────────────
  let rRes;
  try {
    rRes = await api("/auth/register", {
      method: "POST",
      body: JSON.stringify({ username, email, password, ml_verified: true })
    });
    console.log("[REGISTER] register response:", rRes);
  } catch (err) {
    console.error("[REGISTER] register network error:", err);
    setStatus("error", "❌ Gagal membuat akun. Cek koneksi dan coba lagi.");
    resetBtn(); return;
  }

  if (!rRes.ok) {
    const errMsg = rRes.data?.error || "Pendaftaran gagal.";
    console.error("[REGISTER] register error:", errMsg);
    setStatus("error", "❌ " + errMsg);
    resetBtn(); return;
  }

  // ── SUKSES ───────────────────────────────────
  console.log("[REGISTER] SUCCESS! token:", rRes.data.token);
  TOKEN = rRes.data.token;
  localStorage.setItem("ws_token", TOKEN);

  setStatus("success", "🌸 Akun berhasil dibuat! Menyiapkan halaman...");

  // Load user info lalu tampilkan overlay
  try {
    await loadCurrentUser();
  } catch(e) {
    console.warn("[REGISTER] loadCurrentUser failed, using username fallback:", e);
  }

  const displayName = CURRENT_USER?.username || username;
  showSuccessOverlay(displayName);
});

/* ═══════════════════════════════════════════════
   LOGIN
═══════════════════════════════════════════════ */
document.getElementById("btn-login").addEventListener("click", doLogin);
["login-username", "login-password"].forEach(id => {
  document.getElementById(id).addEventListener("keydown", e => {
    if (e.key === "Enter") doLogin();
  });
});

async function doLogin() {
  clearError("login-error");
  const username = document.getElementById("login-username").value.trim();
  const password = document.getElementById("login-password").value;
  if (!username || !password) {
    showError("login-error", "Username dan password wajib diisi."); return;
  }

  const btn = document.getElementById("btn-login");
  btn.disabled = true; btn.textContent = "Masuk...";

  const { ok, data } = await api("/auth/login", {
    method: "POST", body: JSON.stringify({ username, password })
  });

  btn.disabled = false; btn.textContent = "Masuk →";

  if (!ok) { showError("login-error", data.error || "Login gagal."); return; }

  TOKEN = data.token;
  CURRENT_USER = data.user;
  localStorage.setItem("ws_token", TOKEN);
  localStorage.setItem("ws_user", JSON.stringify(CURRENT_USER));
  bootApp();
}

/* ═══════════════════════════════════════════════
   LOGOUT
═══════════════════════════════════════════════ */
document.getElementById("btn-logout").addEventListener("click", () => {
  TOKEN = null; CURRENT_USER = null;
  localStorage.removeItem("ws_token");
  localStorage.removeItem("ws_user");

  // Reset register ke step 1
  document.getElementById("reg-step-2").classList.remove("active");
  document.getElementById("reg-step-1").classList.add("active");
  document.getElementById("dot-2").classList.remove("active");
  document.getElementById("dot-1").classList.remove("done");
  document.getElementById("dot-1").classList.add("active");

  // Kembali ke tab login
  document.querySelectorAll(".auth-tab").forEach(t => t.classList.remove("active"));
  document.querySelector('[data-tab="login"]').classList.add("active");
  document.querySelector(".auth-tab-indicator").classList.remove("right");
  document.querySelectorAll(".form-panel").forEach(p => p.classList.remove("active"));
  document.getElementById("form-login").classList.add("active");

  showScreen("screen-auth");
  toast("Sampai jumpa! 👋");
});

/* ═══════════════════════════════════════════════
   BOOT APP
═══════════════════════════════════════════════ */
async function loadCurrentUser() {
  const { ok, data } = await api("/auth/me");
  if (ok) {
    CURRENT_USER = data;
    localStorage.setItem("ws_user", JSON.stringify(data));
  }
}

/* Overlay sukses register — full screen, tidak bisa dilewat */
function showSuccessOverlay(username) {
  console.log("[OVERLAY] Showing success overlay for:", username);

  // Hapus overlay lama kalau ada
  const old = document.getElementById("success-overlay");
  if (old) old.remove();

  const overlay = document.createElement("div");
  overlay.id = "success-overlay";
  overlay.style.cssText = `
    position:fixed; inset:0; z-index:9999;
    background:linear-gradient(135deg,#F5E0E5 0%,#FDF7F2 100%);
    display:flex; align-items:center; justify-content:center;
  `;

  overlay.innerHTML = `
    <div style="
      text-align:center; padding:48px 40px; max-width:440px; width:90%;
      background:white; border-radius:24px;
      box-shadow:0 20px 60px rgba(200,115,138,.25);
    ">
      <div style="font-size:4rem; margin-bottom:16px;">🌸</div>
      <h2 style="
        font-family:'Playfair Display',serif; font-size:1.8rem;
        color:#2D2020; margin-bottom:12px;
      ">Akun Berhasil Dibuat!</h2>
      <p style="color:#8A7070; font-size:1rem; margin-bottom:6px;">
        Halo, <strong style="color:#C8738A">@${username}</strong>! 👋
      </p>
      <p style="color:#8A7070; font-size:.93rem; line-height:1.7; margin-bottom:24px;">
        Kamu sudah resmi bergabung di <strong>Womenspace</strong>.<br/>
        Ruang aman khusus perempuan untuk berbagi &amp; terhubung.
      </p>
      <div id="overlay-countdown" style="
        background:#F5E0E5; color:#C8738A;
        padding:12px 24px; border-radius:50px;
        font-weight:700; font-size:1rem;
        margin-bottom:20px; display:inline-block;
      ">
        Masuk otomatis dalam <span id="countdown-num">5</span> detik...
      </div>
      <br/>
      <button id="btn-enter-now" style="
        padding:12px 32px; background:#C8738A; color:white;
        border:none; border-radius:50px; font-size:1rem;
        font-weight:700; cursor:pointer; margin-top:4px;
        box-shadow:0 4px 14px rgba(200,115,138,.4);
      ">Masuk Sekarang →</button>
    </div>
  `;

  document.body.appendChild(overlay);
  console.log("[OVERLAY] Overlay appended to DOM");

  // Countdown
  let count = 5;
  const numEl = document.getElementById("countdown-num");

  const timer = setInterval(() => {
    count--;
    if (numEl) numEl.textContent = count;
    if (count <= 0) {
      clearInterval(timer);
      overlay.remove();
      bootApp();
    }
  }, 1000);

  // Tombol masuk sekarang — pakai overlay querySelector bukan getElementById
  const enterBtn = overlay.querySelector("#btn-enter-now");
  if (enterBtn) {
    enterBtn.addEventListener("click", () => {
      clearInterval(timer);
      overlay.remove();
      bootApp();
    });
  }
}

async function bootApp() {
  if (!CURRENT_USER) await loadCurrentUser();
  showScreen("screen-app");
  showPage("page-home");
  updateComposeAvatar();
  loadFeed("fyp");
  loadTrending();
}

function updateComposeAvatar() {
  const el = document.getElementById("compose-avatar-display");
  el.innerHTML = makeAvatar(CURRENT_USER?.avatar_url);
}

/* ═══════════════════════════════════════════════
   NAVBAR
═══════════════════════════════════════════════ */
document.querySelectorAll(".nav-btn[data-page]").forEach(btn => {
  btn.addEventListener("click", () => {
    const page = btn.dataset.page;
    showPage(`page-${page}`);
    if (page === "profile") loadProfile(CURRENT_USER?.id);
    if (page === "search")  loadTrending();
  });
});

/* ═══════════════════════════════════════════════
   FEED TABS
═══════════════════════════════════════════════ */
document.querySelectorAll(".feed-tab").forEach(tab => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".feed-tab").forEach(t => t.classList.remove("active"));
    tab.classList.add("active");
    CURRENT_FEED = tab.dataset.feed;
    document.querySelector(".feed-tab-bar")
      .classList.toggle("right", CURRENT_FEED === "following");
    loadFeed(CURRENT_FEED);
  });
});

async function loadFeed(type) {
  const container = document.getElementById("feed-container");
  container.innerHTML = `<div class="feed-loader">🌸 Memuat postingan...</div>`;
  const { ok, data } = await api(type === "following" ? "/posts/following" : "/posts/fyp");
  if (!ok) { container.innerHTML = `<div class="feed-loader">Gagal memuat feed.</div>`; return; }
  renderPosts(data.posts, container);
}

/* ═══════════════════════════════════════════════
   RENDER POSTS
═══════════════════════════════════════════════ */
function renderPosts(posts, container) {
  if (!posts?.length) {
    container.innerHTML = `<div class="feed-loader">Belum ada postingan di sini ✿</div>`;
    return;
  }
  container.innerHTML = posts.map(renderPostCard).join("");
  attachPostActions(container);
}

function renderPostCard(post) {
  const author = post.author || {};
  const media  = post.media_url ? renderMedia(post.media_url, post.media_type) : "";
  return `
  <div class="post-card" data-post-id="${post.id}">
    <div class="post-header">
      <div class="post-avatar">${makeAvatar(author.avatar_url)}</div>
      <div>
        <div class="post-author-name">@${escHtml(author.username || "unknown")}</div>
        <div class="post-time">${formatTime(post.created_at)}</div>
      </div>
    </div>
    ${post.content ? `<div class="post-content">${escHtml(post.content)}</div>` : ""}
    ${media}
    <div class="post-actions">
      <button class="action-btn like-btn ${post.liked ? "liked" : ""}" data-post-id="${post.id}">
        ${post.liked ? "❤️" : "🤍"} <span class="like-count">${post.like_count}</span>
      </button>
      <button class="action-btn reply-btn"
        data-post-id="${post.id}"
        data-content="${escHtml((post.content || "").substring(0, 80))}">
        💬 ${post.reply_count}
      </button>
      <button class="action-btn repost-btn" data-post-id="${post.id}">
        🔁 ${post.repost_count}
      </button>
    </div>
  </div>`;
}

function renderMedia(url, type) {
  const full = API_BASE.replace("/api", "") + url;
  if (type === "image") return `<div class="post-media"><img src="${full}" alt="media"/></div>`;
  if (type === "video") return `<div class="post-media"><video src="${full}" controls></video></div>`;
  if (type === "audio") return `<div class="post-media"><audio src="${full}" controls></audio></div>`;
  return "";
}

function attachPostActions(container) {
  container.querySelectorAll(".like-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      const pid = btn.dataset.postId;
      const { ok, data } = await api(`/posts/${pid}/like`, { method: "POST" });
      if (!ok) return;
      btn.classList.toggle("liked", data.liked);
      btn.innerHTML = `${data.liked ? "❤️" : "🤍"} <span class="like-count">${data.like_count}</span>`;
    });
  });

  container.querySelectorAll(".reply-btn").forEach(btn => {
    btn.addEventListener("click", () =>
      openReplyModal(btn.dataset.postId, btn.dataset.content));
  });

  container.querySelectorAll(".repost-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      const { ok } = await api(`/posts/${btn.dataset.postId}/repost`, { method: "POST" });
      if (ok) toast("🔁 Repost berhasil!");
    });
  });
}

/* ═══════════════════════════════════════════════
   BUAT POSTINGAN BARU
═══════════════════════════════════════════════ */
let composedMedia = null;

["compose-image", "compose-video", "compose-audio"].forEach(id => {
  document.getElementById(id).addEventListener("change", e => {
    composedMedia = e.target.files[0] || null;
    document.getElementById("compose-media-name").textContent =
      composedMedia?.name || "";
  });
});

document.getElementById("btn-post").addEventListener("click", async () => {
  const text = document.getElementById("compose-text").value.trim();
  if (!text && !composedMedia) { toast("Tulis sesuatu dulu! ✿"); return; }

  const btn = document.getElementById("btn-post");
  btn.disabled = true; btn.textContent = "Posting...";

  const form = new FormData();
  form.append("content", text);
  if (composedMedia) form.append("media", composedMedia);

  const { ok, data } = await api("/posts", { method: "POST", body: form });
  btn.disabled = false; btn.textContent = "Post ✿";

  if (!ok) { toast(data.error || "Gagal posting."); return; }

  document.getElementById("compose-text").value = "";
  document.getElementById("compose-media-name").textContent = "";
  composedMedia = null;
  toast("🌸 Postingan berhasil dikirim!");
  loadFeed(CURRENT_FEED);
});

/* ═══════════════════════════════════════════════
   REPLY MODAL
═══════════════════════════════════════════════ */
function openReplyModal(postId, originalContent) {
  REPLY_TARGET = postId;
  document.getElementById("reply-original").innerHTML = originalContent
    ? `<em>"${escHtml(originalContent)}..."</em>` : "";
  document.getElementById("reply-text").value = "";
  clearError("reply-error");
  document.getElementById("modal-reply").classList.remove("hidden");
}

document.getElementById("modal-close-reply").addEventListener("click", () => {
  document.getElementById("modal-reply").classList.add("hidden");
});

document.getElementById("btn-submit-reply").addEventListener("click", async () => {
  const text = document.getElementById("reply-text").value.trim();
  if (!text) { showError("reply-error", "Balasan tidak boleh kosong."); return; }

  const form = new FormData();
  form.append("content", text);
  const { ok, data } = await api(`/posts/${REPLY_TARGET}/reply`,
    { method: "POST", body: form });

  if (!ok) { showError("reply-error", data.error || "Gagal mengirim balasan."); return; }
  document.getElementById("modal-reply").classList.add("hidden");
  toast("💬 Balasan terkirim!");
  loadFeed(CURRENT_FEED);
});

/* ═══════════════════════════════════════════════
   SEARCH & TRENDING
═══════════════════════════════════════════════ */
async function loadTrending() {
  const container = document.getElementById("trending-container");
  container.innerHTML = `<div class="feed-loader">Memuat trending... ✨</div>`;
  const { ok, data } = await api("/search/trending");
  if (!ok) { container.innerHTML = `<div class="feed-loader">Gagal memuat trending.</div>`; return; }
  renderPosts(data.posts, container);
}

document.getElementById("btn-search").addEventListener("click", doSearch);
document.getElementById("search-input").addEventListener("keydown", e => {
  if (e.key === "Enter") doSearch();
});

async function doSearch() {
  const q = document.getElementById("search-input").value.trim();
  if (!q) return;
  const { ok, data } = await api(`/search?q=${encodeURIComponent(q)}`);
  if (!ok) return;

  document.getElementById("search-results-section").classList.remove("hidden");

  const usersEl = document.getElementById("search-users");
  usersEl.innerHTML = data.users.length
    ? data.users.map(u => `
        <div class="user-card">
          <div class="user-avatar">${makeAvatar(u.avatar_url)}</div>
          <div class="user-info">
            <div class="user-username">@${escHtml(u.username)}</div>
            <div style="font-size:.82rem;color:var(--text-muted)">${u.bio || ""}</div>
          </div>
        </div>`).join("") : "";

  renderPosts(data.posts, document.getElementById("search-posts"));
}

/* ═══════════════════════════════════════════════
   PROFILE
═══════════════════════════════════════════════ */
async function loadProfile(userId) {
  if (!userId) return;
  const container = document.getElementById("profile-posts-feed");
  container.innerHTML = `<div class="feed-loader">Memuat profil... 🌸</div>`;

  const { ok, data } = await api(`/users/${userId}`);
  if (!ok) { container.innerHTML = `<div class="feed-loader">Gagal memuat profil.</div>`; return; }

  document.getElementById("profile-username").textContent    = `@${data.username}`;
  document.getElementById("profile-bio").textContent         = data.bio || "";
  document.getElementById("profile-posts-count").textContent = data.posts?.length || 0;
  document.getElementById("profile-followers").textContent   = data.followers;
  document.getElementById("profile-following").textContent   = data.following;
  document.getElementById("profile-avatar").innerHTML        = makeAvatar(data.avatar_url);

  renderPosts(data.posts, container);
}

/* ── Edit Profile ──────────────────────────────── */
document.getElementById("btn-edit-profile").addEventListener("click", () => {
  ["edit-username","edit-email","edit-new-password","edit-old-password"]
    .forEach(id => document.getElementById(id).value = "");
  clearError("edit-error");
  document.getElementById("modal-edit-profile").classList.remove("hidden");
});
document.getElementById("modal-close-edit").addEventListener("click", () => {
  document.getElementById("modal-edit-profile").classList.add("hidden");
});

document.getElementById("btn-save-profile").addEventListener("click", async () => {
  clearError("edit-error");
  const old_password = document.getElementById("edit-old-password").value;
  if (!old_password) {
    showError("edit-error", "Password lama wajib diisi untuk verifikasi."); return;
  }

  const body = {
    old_password,
    username    : document.getElementById("edit-username").value.trim()   || undefined,
    email       : document.getElementById("edit-email").value.trim()      || undefined,
    new_password: document.getElementById("edit-new-password").value      || undefined,
  };

  const btn = document.getElementById("btn-save-profile");
  btn.disabled = true; btn.textContent = "Menyimpan...";
  const { ok, data } = await api("/users/me/update",
    { method: "PUT", body: JSON.stringify(body) });
  btn.disabled = false; btn.textContent = "Simpan Perubahan";

  if (!ok) { showError("edit-error", data.error || "Gagal menyimpan."); return; }

  await loadCurrentUser();
  document.getElementById("modal-edit-profile").classList.add("hidden");
  loadProfile(CURRENT_USER.id);
  toast("✅ Profil berhasil diperbarui!");
});

/* ── Hapus Akun ────────────────────────────────── */
document.getElementById("btn-delete-account").addEventListener("click", () => {
  document.getElementById("modal-edit-profile").classList.add("hidden");
  document.getElementById("delete-password").value = "";
  clearError("delete-error");
  document.getElementById("modal-delete-confirm").classList.remove("hidden");
});
document.getElementById("btn-cancel-delete").addEventListener("click", () => {
  document.getElementById("modal-delete-confirm").classList.add("hidden");
});
document.getElementById("btn-confirm-delete").addEventListener("click", async () => {
  const pw = document.getElementById("delete-password").value;
  if (!pw) { showError("delete-error", "Masukkan password untuk konfirmasi."); return; }

  const { ok, data } = await api("/users/me/delete",
    { method: "DELETE", body: JSON.stringify({ password: pw }) });
  if (!ok) { showError("delete-error", data.error || "Gagal menghapus akun."); return; }

  TOKEN = null; CURRENT_USER = null;
  localStorage.removeItem("ws_token");
  localStorage.removeItem("ws_user");
  document.getElementById("modal-delete-confirm").classList.add("hidden");
  showScreen("screen-auth");
  toast("Akunmu telah dihapus secara permanen.");
});

/* ═══════════════════════════════════════════════
   TAMBAHAN CSS untuk step indicator (inject)
═══════════════════════════════════════════════ */
const extraCSS = `
.step-indicator {
  display: flex; align-items: center; gap: 0; margin-bottom: 20px;
}
.step-dot {
  width: 28px; height: 28px; border-radius: 50%;
  background: var(--cream-dark); color: var(--text-muted);
  font-size: .8rem; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  border: 2px solid var(--border);
  transition: all .25s;
}
.step-dot.active { background: var(--rose); color: white; border-color: var(--rose); }
.step-dot.done   { background: var(--success); color: white; border-color: var(--success); }
.step-line { flex: 1; height: 2px; background: var(--border); margin: 0 8px; }
.step-label { font-size: .8rem; color: var(--text-muted); margin-bottom: 16px;
              font-weight: 600; text-transform: uppercase; letter-spacing: .05em; }
`;
const styleEl = document.createElement("style");
styleEl.textContent = extraCSS;
document.head.appendChild(styleEl);

/* ═══════════════════════════════════════════════
   INIT — cek token saat halaman dibuka
═══════════════════════════════════════════════ */
(async () => {
  if (TOKEN) {
    const { ok } = await api("/auth/me");
    if (ok) { await bootApp(); return; }
    localStorage.removeItem("ws_token");
    TOKEN = null;
  }
  showScreen("screen-auth");
})();
