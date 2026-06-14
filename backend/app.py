"""
╔══════════════════════════════════════════════════════════╗
║          WOMENSPACE — Backend API (Flask + SQLite)       ║
║          Senior Full-Stack Architecture                  ║
╚══════════════════════════════════════════════════════════╝

SETUP:
  pip install -r requirements.txt

RUN:
  python app.py

MODEL FILES (letakkan di folder backend/ bersama app.py):
  gender_model.h5                        ← Keras/TensorFlow CNN Model
  haarcascade_frontalface_default.xml    ← OpenCV cascade
  haarcascade_profileface.xml            ← OpenCV cascade (optional)
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_jwt_extended import (
    JWTManager, create_access_token,
    jwt_required, get_jwt_identity
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3, os, uuid, json
from datetime import datetime, timedelta, timezone

# WIB = UTC+7
WIB = timezone(timedelta(hours=7))

def now_wib():
    """Return current time in WIB as string."""
    return datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S")

# ── ML dependencies ───────────────────────────────────────
import cv2
import numpy as np
from tensorflow.keras.models import load_model

# ─────────────────────────────────────────────
# APP CONFIG
# ─────────────────────────────────────────────
app = Flask(__name__)

# ── CORS: allow semua origin (development mode) ───────────
@app.after_request
def cors(response):
    origin = request.headers.get("Origin", "")
    response.headers["Access-Control-Allow-Origin"]  = origin or "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    return response

@app.route("/api/<path:path>", methods=["OPTIONS"])
def preflight(path):
    return jsonify({}), 200

app.config["JWT_SECRET_KEY"]        = "womenspace-super-secret-2025"
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=12)
app.config["UPLOAD_FOLDER"]         = "uploads"
app.config["MAX_CONTENT_LENGTH"]    = 50 * 1024 * 1024   # 50 MB

ALLOWED_IMG  = {"png", "jpg", "jpeg", "gif", "webp"}
ALLOWED_VID  = {"mp4", "mov", "webm"}
ALLOWED_AUD  = {"mp3", "wav", "ogg", "m4a"}
ALLOWED_FACE = {"png", "jpg", "jpeg", "webp"}

jwt = JWTManager(app)
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

DB_PATH = "womenspace.db"

# ── Serve frontend langsung dari Flask ────────────────────
FRONTEND_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "frontend")
)
print(f"📁  Frontend dir : {FRONTEND_DIR}")

@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.route("/<path:filename>")
def frontend_files(filename):
    if filename.startswith("api/"):
        return jsonify({"error": "Not found"}), 404
    return send_from_directory(FRONTEND_DIR, filename)

# ─────────────────────────────────────────────────────────
# ML MODEL LOADER (.h5)
# ─────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))

# Sesuaikan IMG_SIZE ini dengan ukuran input model CNN kamu saat di-train (misal 128 atau 224)
IMG_SIZE   = 64 

_model_path = os.path.join(BASE_DIR, "gender_model.h5")
_cascade_path = os.path.join(BASE_DIR, "haarcascade_frontalface_default.xml")

try:
    GENDER_MODEL = load_model(_model_path, compile=False)
    print(f"✅  gender_model.h5 loaded")
except Exception as e:
    GENDER_MODEL = None
    print(f"⚠️   gender_model.h5 tidak ditemukan atau error: {e}")

try:
    FACE_CASCADE = cv2.CascadeClassifier(_cascade_path)
    if FACE_CASCADE.empty():
        raise ValueError("Cascade file kosong / path salah")
    print(f"✅  Haar cascade loaded")
except Exception as e:
    FACE_CASCADE = None
    print(f"⚠️   Haar cascade gagal dimuat: {e}")

# Load profile cascade (deteksi wajah samping)
_profile_path = os.path.join(BASE_DIR, "haarcascade_profileface.xml")
try:
    PROFILE_CASCADE = cv2.CascadeClassifier(_profile_path)
    if PROFILE_CASCADE.empty():
        raise ValueError("empty")
    print("✅  Profile cascade loaded")
except Exception:
    PROFILE_CASCADE = None
    print("ℹ️   haarcascade_profileface.xml tidak ada — hanya deteksi wajah depan")


def predict_gender(image_path: str) -> dict:
    """
    Pipeline Deep Learning (.h5):
      1. Baca gambar → convert RGB.
      2. Buat versi grayscale untuk Haar Cascade (deteksi wajah).
      3. Crop wajah terbesar dari gambar *berwarna* (RGB).
      4. Resize ke IMG_SIZE x IMG_SIZE.
      5. Normalisasi (/ 255.0) dan tambah dimensi batch (1, 128, 128, 3).
      6. Predict dengan Keras model.
    """
    img_bgr = cv2.imread(image_path)
    if img_bgr is None:
        return {"error": "Gambar tidak bisa dibaca. Coba format JPG atau PNG."}

    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    gray_balanced = cv2.equalizeHist(gray)

    faces = []
    if FACE_CASCADE is not None:
        faces = FACE_CASCADE.detectMultiScale(
            gray_balanced, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40)
        )

    if len(faces) == 0 and PROFILE_CASCADE is not None:
        faces = PROFILE_CASCADE.detectMultiScale(
            gray_balanced, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40)
        )

    if len(faces) == 0:
        return {"error": "Wajah tidak terdeteksi. Pastikan wajah terlihat jelas dengan pencahayaan yang cukup."}

    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])

    # Ambil wajah dari grayscale/equalized image, karena CNN expect 1 channel
    face_crop = gray_balanced[y:y+h, x:x+w]

    # Resize ke input model CNN: 64x64
    face_resized = cv2.resize(face_crop, (IMG_SIZE, IMG_SIZE))

    # Normalisasi
    face_array = face_resized.astype("float32") / 255.0

    # Bentuk input CNN: (1, 64, 64, 1)
    features = np.expand_dims(face_array, axis=(0, -1))

    # Predict
    prediction = float(GENDER_MODEL.predict(features, verbose=0).ravel()[0])

    # Mapping CNN: 0 = female, 1 = male
    if prediction >= 0.5:
        gender = "male"
        confidence = prediction
    else:
        gender = "female"
        confidence = 1.0 - prediction

    print(f"[CNN] raw_prediction={prediction:.6f} -> {gender} ({confidence:.4f})")

    return {
        "gender": gender,
        "confidence": confidence
    }

# ─────────────────────────────────────────────
# DATABASE HELPERS
# ─────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    """Create all tables if not exist."""
    with get_db() as db:
        db.executescript("""
        -- USERS
        CREATE TABLE IF NOT EXISTS users (
            id          TEXT PRIMARY KEY,
            username    TEXT UNIQUE NOT NULL,
            email       TEXT UNIQUE NOT NULL,
            password    TEXT NOT NULL,
            avatar_url  TEXT DEFAULT NULL,
            bio         TEXT DEFAULT '',
            is_psikolog INTEGER DEFAULT 0,
            created_at  TEXT DEFAULT (datetime('now'))
        );

        -- FOLLOWS
        CREATE TABLE IF NOT EXISTS follows (
            follower_id  TEXT NOT NULL,
            following_id TEXT NOT NULL,
            created_at   TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (follower_id, following_id),
            FOREIGN KEY (follower_id)  REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (following_id) REFERENCES users(id) ON DELETE CASCADE
        );

        -- POSTS
        CREATE TABLE IF NOT EXISTS posts (
            id           TEXT PRIMARY KEY,
            user_id      TEXT NOT NULL,
            content      TEXT NOT NULL,
            media_url    TEXT DEFAULT NULL,
            media_type   TEXT DEFAULT NULL,
            parent_id    TEXT DEFAULT NULL,
            repost_of    TEXT DEFAULT NULL,
            is_anonymous INTEGER DEFAULT 0,
            created_at   TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id)   REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (parent_id) REFERENCES posts(id) ON DELETE CASCADE,
            FOREIGN KEY (repost_of) REFERENCES posts(id) ON DELETE CASCADE
        );

        -- LIKES
        CREATE TABLE IF NOT EXISTS likes (
            user_id    TEXT NOT NULL,
            post_id    TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (user_id, post_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
        );

        -- BOOKMARKS
        CREATE TABLE IF NOT EXISTS bookmarks (
            user_id    TEXT NOT NULL,
            post_id    TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (user_id, post_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
        );

        -- NOTIFICATIONS
        CREATE TABLE IF NOT EXISTS notifications (
            id           TEXT PRIMARY KEY,
            user_id      TEXT NOT NULL,
            actor_id     TEXT NOT NULL,
            type         TEXT NOT NULL,
            ref_id       TEXT DEFAULT NULL,
            preview      TEXT DEFAULT NULL,
            is_read      INTEGER DEFAULT 0,
            created_at   TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id)  REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (actor_id) REFERENCES users(id) ON DELETE CASCADE
        );

        -- DM CONVERSATIONS
        CREATE TABLE IF NOT EXISTS dm_conversations (
            id         TEXT PRIMARY KEY,
            user1_id   TEXT NOT NULL,
            user2_id   TEXT NOT NULL,
            type       TEXT DEFAULT 'dm',
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE (user1_id, user2_id),
            FOREIGN KEY (user1_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (user2_id) REFERENCES users(id) ON DELETE CASCADE
        );

        -- DM MESSAGES
        CREATE TABLE IF NOT EXISTS dm_messages (
            id               TEXT PRIMARY KEY,
            conv_id          TEXT NOT NULL,
            sender_id        TEXT NOT NULL,
            content          TEXT NOT NULL,
            reply_to_id      TEXT DEFAULT NULL,
            reply_to_content TEXT DEFAULT NULL,
            reply_to_sender  TEXT DEFAULT NULL,
            is_read          INTEGER DEFAULT 0,
            created_at       TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (conv_id)   REFERENCES dm_conversations(id) ON DELETE CASCADE,
            FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE
        );

        -- STORIES
        CREATE TABLE IF NOT EXISTS stories (
            id         TEXT PRIMARY KEY,
            user_id    TEXT NOT NULL,
            media_url  TEXT NOT NULL,
            media_type TEXT DEFAULT 'image',
            caption    TEXT DEFAULT '',
            expires_at TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        -- STORY VIEWS
        CREATE TABLE IF NOT EXISTS story_views (
            story_id   TEXT NOT NULL,
            user_id    TEXT NOT NULL,
            viewed_at  TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (story_id, user_id)
        );

        -- PSIKOLOG PROFILES
        CREATE TABLE IF NOT EXISTS psikolog_profiles (
            id             TEXT PRIMARY KEY,
            user_id        TEXT UNIQUE NOT NULL,
            name           TEXT NOT NULL,
            specialization TEXT NOT NULL,
            bio            TEXT DEFAULT '',
            experience     INTEGER DEFAULT 0,
            rating         REAL DEFAULT 5.0,
            session_count  INTEGER DEFAULT 0,
            price          INTEGER DEFAULT 0,
            available      INTEGER DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        -- KONSULTASI SESSIONS
        CREATE TABLE IF NOT EXISTS konsultasi_sessions (
            id              TEXT PRIMARY KEY,
            psikolog_id     TEXT NOT NULL,
            user_id         TEXT NOT NULL,
            conversation_id TEXT DEFAULT NULL,
            date            TEXT NOT NULL,
            time            TEXT NOT NULL,
            topic           TEXT NOT NULL,
            type            TEXT DEFAULT 'chat',
            status          TEXT DEFAULT 'scheduled',
            created_at      TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (psikolog_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id)     REFERENCES users(id) ON DELETE CASCADE
        );

        -- PINNED POSTS
        CREATE TABLE IF NOT EXISTS pinned_posts (
            user_id    TEXT NOT NULL,
            post_id    TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (user_id, post_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
        );

        -- POLLS
        CREATE TABLE IF NOT EXISTS polls (
            id         TEXT PRIMARY KEY,
            post_id    TEXT NOT NULL UNIQUE,
            question   TEXT NOT NULL,
            ends_at    TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
        );

        -- POLL OPTIONS
        CREATE TABLE IF NOT EXISTS poll_options (
            id      TEXT PRIMARY KEY,
            poll_id TEXT NOT NULL,
            label   TEXT NOT NULL,
            FOREIGN KEY (poll_id) REFERENCES polls(id) ON DELETE CASCADE
        );

        -- POLL VOTES
        CREATE TABLE IF NOT EXISTS poll_votes (
            user_id   TEXT NOT NULL,
            poll_id   TEXT NOT NULL,
            option_id TEXT NOT NULL,
            voted_at  TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (user_id, poll_id),
            FOREIGN KEY (user_id)   REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (poll_id)   REFERENCES polls(id) ON DELETE CASCADE,
            FOREIGN KEY (option_id) REFERENCES poll_options(id) ON DELETE CASCADE
        );
        """)
    print("✅  Database initialized — womenspace.db")


# ─────────────────────────────────────────────
# UTILS
# ─────────────────────────────────────────────
def allowed_file(filename, allowed):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed

def save_upload(file, allowed_set, subfolder="media"):
    if not allowed_file(file.filename, allowed_set):
        return None, None, "File type not allowed"
    ext   = file.filename.rsplit(".", 1)[1].lower()
    fname = f"{uuid.uuid4().hex}.{ext}"
    folder = os.path.join(app.config["UPLOAD_FOLDER"], subfolder)
    os.makedirs(folder, exist_ok=True)
    abs_path = os.path.join(folder, fname)
    file.save(abs_path)
    url_path = f"/uploads/{subfolder}/{fname}"
    return url_path, abs_path, None

def row_to_dict(row):
    return dict(row) if row else None

def enrich_post(post_dict, current_user_id, db):
    pid = post_dict["id"]
    post_dict["like_count"]   = db.execute("SELECT COUNT(*) FROM likes WHERE post_id=?", (pid,)).fetchone()[0]
    post_dict["reply_count"]  = db.execute("SELECT COUNT(*) FROM posts WHERE parent_id=?", (pid,)).fetchone()[0]
    post_dict["repost_count"] = db.execute("SELECT COUNT(*) FROM posts WHERE repost_of=?", (pid,)).fetchone()[0]
    post_dict["liked"]        = bool(db.execute("SELECT 1 FROM likes WHERE user_id=? AND post_id=?", (current_user_id, pid)).fetchone())
    post_dict["bookmarked"]   = bool(db.execute("SELECT 1 FROM bookmarks WHERE user_id=? AND post_id=?", (current_user_id, pid)).fetchone())
    post_dict["pinned"]       = bool(db.execute("SELECT 1 FROM pinned_posts WHERE post_id=?", (pid,)).fetchone())
    post_dict["is_anonymous"] = bool(post_dict.get("is_anonymous", 0))

    poll_row = db.execute("SELECT * FROM polls WHERE post_id=?", (pid,)).fetchone()
    if poll_row:
        options = db.execute("""
            SELECT o.id, o.label, COUNT(v.option_id) as votes
            FROM poll_options o
            LEFT JOIN poll_votes v ON v.option_id = o.id
            WHERE o.poll_id=? GROUP BY o.id
        """, (poll_row["id"],)).fetchall()
        my_vote = db.execute(
            "SELECT option_id FROM poll_votes WHERE user_id=? AND poll_id=?",
            (current_user_id, poll_row["id"])).fetchone()
        total   = sum(o["votes"] for o in options)
        post_dict["poll"] = {
            "id"      : poll_row["id"],
            "question": poll_row["question"],
            "ends_at" : poll_row["ends_at"],
            "is_ended": poll_row["ends_at"] < now_wib(),
            "my_vote" : my_vote["option_id"] if my_vote else None,
            "total"   : total,
            "options" : [{"id":o["id"],"label":o["label"],"votes":o["votes"],
                           "percent": round(o["votes"]/total*100) if total else 0}
                          for o in options]
        }
    else:
        post_dict["poll"] = None

    if post_dict["is_anonymous"]:
        post_dict["author"] = None
    else:
        author = db.execute("SELECT id,username,avatar_url FROM users WHERE id=?", (post_dict["user_id"],)).fetchone()
        post_dict["author"] = row_to_dict(author)
    return post_dict


# ─────────────────────────────────────────────
# STATIC FILES (uploads)
# ─────────────────────────────────────────────
@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# ═══════════════════════════════════════════════════════════
# AUTH ENDPOINTS
# ═══════════════════════════════════════════════════════════

@app.route("/api/auth/verify-face", methods=["POST"])
def verify_face():
    if "face_photo" not in request.files:
        return jsonify({"error": "Tidak ada foto yang dikirim."}), 400

    file = request.files["face_photo"]
    if not allowed_file(file.filename, ALLOWED_FACE):
        return jsonify({"error": "Format gambar tidak didukung. Gunakan JPG, PNG, atau WEBP."}), 400

    if GENDER_MODEL is None:
        return jsonify({
            "error": "Model ML belum siap. Pastikan gender_model.h5 ada di folder backend."
        }), 503

    url_path, abs_path, err = save_upload(file, ALLOWED_FACE, subfolder="temp_faces")
    if err:
        return jsonify({"error": err}), 400

    result = predict_gender(abs_path)

    if "error" in result:
        return jsonify({
            "allowed"   : False,
            "gender"    : None,
            "confidence": 0.0,
            "message"   : result["error"]
        }), 422

    gender     = result["gender"]
    confidence = result["confidence"]

    if gender == "male":
        return jsonify({
            "allowed"   : False,
            "gender"    : "male",
            "confidence": round(confidence, 4),
            "message"   : "Maaf, platform Womenspace eksklusif untuk perempuan."
        }), 403

    return jsonify({
        "allowed"   : True,
        "gender"    : "female",
        "confidence": round(confidence, 4),
        "message"   : f"Verifikasi berhasil! Kamu terdeteksi sebagai perempuan ({round(confidence*100,1)}%)."
    }), 200


@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json()
    username = (data.get("username") or "").strip()
    email    = (data.get("email")    or "").strip().lower()
    password =  data.get("password") or ""
    verified =  data.get("ml_verified", False)

    if not all([username, email, password]):
        return jsonify({"error": "Semua field wajib diisi."}), 400
    if len(password) < 8:
        return jsonify({"error": "Password minimal 8 karakter."}), 400
    if not verified:
        return jsonify({"error": "Verifikasi wajah belum dilakukan."}), 400

    hashed = generate_password_hash(password)
    uid    = uuid.uuid4().hex

    with get_db() as db:
        try:
            db.execute(
                "INSERT INTO users (id,username,email,password) VALUES (?,?,?,?)",
                (uid, username, email, hashed)
            )
        except sqlite3.IntegrityError as e:
            if "username" in str(e):
                return jsonify({"error": "Username sudah dipakai."}), 409
            return jsonify({"error": "Email sudah terdaftar."}), 409

    token = create_access_token(identity=uid)
    return jsonify({"message": "Registrasi berhasil!", "token": token, "user_id": uid}), 201

@app.route("/api/auth/login", methods=["POST"])
def login():
    data     = request.get_json()
    username = (data.get("username") or "").strip()
    password =  data.get("password") or ""

    with get_db() as db:
        user = db.execute(
            "SELECT * FROM users WHERE username=?", (username,)).fetchone()

    if not user or not check_password_hash(user["password"], password):
        return jsonify({"error": "Username atau password salah."}), 401

    token = create_access_token(identity=user["id"])
    return jsonify({
        "message" : "Login berhasil!",
        "token"   : token,
        "user"    : {
            "id"        : user["id"],
            "username"  : user["username"],
            "email"     : user["email"],
            "avatar_url": user["avatar_url"],
            "bio"       : user["bio"],
        }
    }), 200

@app.route("/api/auth/me", methods=["GET"])
@jwt_required()
def me():
    uid = get_jwt_identity()
    with get_db() as db:
        user = db.execute(
            "SELECT id,username,email,avatar_url,bio,created_at FROM users WHERE id=?",
            (uid,)).fetchone()
    if not user:
        return jsonify({"error": "User tidak ditemukan."}), 404
    return jsonify(row_to_dict(user)), 200


# ═══════════════════════════════════════════════════════════
# POSTS ENDPOINTS
# ═══════════════════════════════════════════════════════════

@app.route("/api/posts", methods=["POST"])
@jwt_required()
def create_post():
    uid        = get_jwt_identity()
    content    = (request.form.get("content") or "").strip()
    is_anon    = request.form.get("is_anonymous", "0") == "1"
    if not content:
        return jsonify({"error": "Konten tidak boleh kosong."}), 400

    media_url  = None
    media_type = None

    if "media" in request.files:
        f = request.files["media"]
        if allowed_file(f.filename, ALLOWED_IMG):
            media_url, _, err = save_upload(f, ALLOWED_IMG)
            media_type = "image"
        elif allowed_file(f.filename, ALLOWED_VID):
            media_url, _, err = save_upload(f, ALLOWED_VID)
            media_type = "video"
        elif allowed_file(f.filename, ALLOWED_AUD):
            media_url, _, err = save_upload(f, ALLOWED_AUD)
            media_type = "audio"
        else:
            return jsonify({"error": "Format file tidak didukung."}), 400
        if err:
            return jsonify({"error": err}), 400

    pid = uuid.uuid4().hex
    with get_db() as db:
        db.execute(
            "INSERT INTO posts (id,user_id,content,media_url,media_type,is_anonymous,created_at) VALUES (?,?,?,?,?,?,?)",
            (pid, uid, content, media_url, media_type, 1 if is_anon else 0, now_wib())
        )
    return jsonify({"message": "Post berhasil dibuat!", "post_id": pid}), 201

@app.route("/api/posts/fyp", methods=["GET"])
@jwt_required()
def fyp():
    uid    = get_jwt_identity()
    page   = int(request.args.get("page", 1))
    limit  = 20
    offset = (page - 1) * limit

    with get_db() as db:
        rows = db.execute("""
            SELECT * FROM posts
            WHERE parent_id IS NULL AND repost_of IS NULL
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset)).fetchall()
        posts = [enrich_post(dict(r), uid, db) for r in rows]

    return jsonify({"posts": posts, "page": page}), 200

@app.route("/api/posts/following", methods=["GET"])
@jwt_required()
def following_feed():
    uid    = get_jwt_identity()
    page   = int(request.args.get("page", 1))
    limit  = 20
    offset = (page - 1) * limit

    with get_db() as db:
        rows = db.execute("""
            SELECT p.* FROM posts p
            JOIN follows f ON p.user_id = f.following_id
            WHERE f.follower_id=? AND p.parent_id IS NULL
            ORDER BY p.created_at DESC
            LIMIT ? OFFSET ?
        """, (uid, limit, offset)).fetchall()
        posts = [enrich_post(dict(r), uid, db) for r in rows]

    return jsonify({"posts": posts, "page": page}), 200

@app.route("/api/users/by-username/<username>", methods=["GET"])
@jwt_required()
def get_user_by_username(username):
    uid = get_jwt_identity()
    with get_db() as db:
        user = db.execute(
            "SELECT id FROM users WHERE username=?", (username,)).fetchone()
        if not user:
            return jsonify({"error": "User tidak ditemukan."}), 404
    return jsonify({"id": user["id"]}), 200

@app.route("/api/posts/<post_id>", methods=["GET"])
@jwt_required()
def get_single_post(post_id):
    uid = get_jwt_identity()
    with get_db() as db:
        row = db.execute("SELECT * FROM posts WHERE id=?", (post_id,)).fetchone()
        if not row:
            return jsonify({"error": "Post tidak ditemukan."}), 404
        post = enrich_post(dict(row), uid, db)
    return jsonify(post), 200

@app.route("/api/notifications/<notif_id>/read", methods=["POST"])
@jwt_required()
def read_notification(notif_id):
    uid = get_jwt_identity()
    with get_db() as db:
        db.execute(
            "UPDATE notifications SET is_read=1 WHERE id=? AND user_id=?",
            (notif_id, uid))
    return jsonify({"ok": True}), 200

@app.route("/api/posts/<post_id>/like", methods=["POST"])
@jwt_required()
def toggle_like(post_id):
    uid = get_jwt_identity()
    with get_db() as db:
        existing = db.execute(
            "SELECT 1 FROM likes WHERE user_id=? AND post_id=?", (uid, post_id)).fetchone()
        if existing:
            db.execute("DELETE FROM likes WHERE user_id=? AND post_id=?", (uid, post_id))
            liked = False
        else:
            db.execute("INSERT INTO likes (user_id,post_id) VALUES (?,?)", (uid, post_id))
            liked = True
            post = db.execute("SELECT user_id, content FROM posts WHERE id=?", (post_id,)).fetchone()
            if post and post["user_id"] != uid:
                preview = (post["content"] or "")[:60]
                create_notification(db, post["user_id"], uid, "like", ref_id=post_id, preview=preview)

        count = db.execute(
            "SELECT COUNT(*) FROM likes WHERE post_id=?", (post_id,)).fetchone()[0]
    return jsonify({"liked": liked, "like_count": count}), 200

@app.route("/api/posts/<post_id>/reply", methods=["POST"])
@jwt_required()
def reply_post(post_id):
    uid     = get_jwt_identity()
    content = (request.form.get("content") or "").strip()
    if not content:
        return jsonify({"error": "Reply tidak boleh kosong."}), 400

    rid = uuid.uuid4().hex
    with get_db() as db:
        db.execute(
            "INSERT INTO posts (id,user_id,content,parent_id,created_at) VALUES (?,?,?,?,?)",
            (rid, uid, content, post_id, now_wib())
        )
        post = db.execute("SELECT user_id, content FROM posts WHERE id=?", (post_id,)).fetchone()
        if post and post["user_id"] != uid:
            create_notification(db, post["user_id"], uid, "reply",
                                ref_id=post_id, preview=content[:60])
    return jsonify({"message": "Reply berhasil!", "reply_id": rid}), 201

@app.route("/api/posts/<post_id>/repost", methods=["POST"])
@jwt_required()
def repost(post_id):
    uid = get_jwt_identity()
    rid = uuid.uuid4().hex
    with get_db() as db:
        db.execute(
            "INSERT INTO posts (id,user_id,content,repost_of) VALUES (?,?,?,?)",
            (rid, uid, "", post_id)
        )
    return jsonify({"message": "Repost berhasil!", "repost_id": rid}), 201

@app.route("/api/posts/<post_id>/replies", methods=["GET"])
@jwt_required()
def get_replies(post_id):
    uid = get_jwt_identity()
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM posts WHERE parent_id=? ORDER BY created_at ASC",
            (post_id,)).fetchall()
        replies = [enrich_post(dict(r), uid, db) for r in rows]
    return jsonify({"replies": replies}), 200


# ═══════════════════════════════════════════════════════════
# SEARCH ENDPOINT
# ═══════════════════════════════════════════════════════════

@app.route("/api/search", methods=["GET"])
@jwt_required()
def search():
    uid = get_jwt_identity()
    q   = (request.args.get("q") or "").strip()
    if not q:
        return jsonify({"posts": [], "users": []}), 200

    pattern = f"%{q}%"
    with get_db() as db:
        post_rows = db.execute("""
            SELECT * FROM posts
            WHERE content LIKE ? AND parent_id IS NULL
            ORDER BY created_at DESC LIMIT 30
        """, (pattern,)).fetchall()
        user_rows = db.execute("""
            SELECT id,username,avatar_url,bio FROM users
            WHERE username LIKE ? LIMIT 10
        """, (pattern,)).fetchall()

        posts = [enrich_post(dict(r), uid, db) for r in post_rows]
        users = [dict(r) for r in user_rows]

    return jsonify({"posts": posts, "users": users}), 200

@app.route("/api/search/trending", methods=["GET"])
@jwt_required()
def trending():
    uid = get_jwt_identity()
    with get_db() as db:
        rows = db.execute("""
            SELECT p.*, COUNT(l.post_id) as lc
            FROM posts p
            LEFT JOIN likes l ON l.post_id=p.id
            WHERE p.parent_id IS NULL
              AND p.created_at >= datetime('now','-7 days')
            GROUP BY p.id
            ORDER BY lc DESC, p.created_at DESC
            LIMIT 20
        """).fetchall()
        posts = [enrich_post(dict(r), uid, db) for r in rows]
    return jsonify({"posts": posts}), 200


# ═══════════════════════════════════════════════════════════
# PROFILE ENDPOINTS
# ═══════════════════════════════════════════════════════════

@app.route("/api/users/<user_id>", methods=["GET"])
@jwt_required()
def get_profile(user_id):
    uid = get_jwt_identity()
    if user_id == "me":
        user_id = uid

    with get_db() as db:
        user = db.execute(
            "SELECT id,username,email,avatar_url,bio,created_at FROM users WHERE id=?",
            (user_id,)).fetchone()
        if not user:
            return jsonify({"error": "User tidak ditemukan."}), 404

        if uid == user_id:
            posts_rows = db.execute(
                "SELECT * FROM posts WHERE user_id=? AND parent_id IS NULL AND repost_of IS NULL ORDER BY created_at DESC",
                (user_id,)).fetchall()
            replies_rows = db.execute(
                "SELECT * FROM posts WHERE user_id=? AND parent_id IS NOT NULL ORDER BY created_at DESC LIMIT 20",
                (user_id,)).fetchall()
        else:
            posts_rows = db.execute(
                "SELECT * FROM posts WHERE user_id=? AND parent_id IS NULL AND repost_of IS NULL AND is_anonymous=0 ORDER BY created_at DESC",
                (user_id,)).fetchall()
            replies_rows = db.execute(
                "SELECT * FROM posts WHERE user_id=? AND parent_id IS NOT NULL AND is_anonymous=0 ORDER BY created_at DESC LIMIT 20",
                (user_id,)).fetchall()

        posts   = [enrich_post(dict(r), uid, db) for r in posts_rows]
        replies = [enrich_post(dict(r), uid, db) for r in replies_rows]

        followers = db.execute(
            "SELECT COUNT(*) FROM follows WHERE following_id=?", (user_id,)).fetchone()[0]
        following = db.execute(
            "SELECT COUNT(*) FROM follows WHERE follower_id=?", (user_id,)).fetchone()[0]
        is_following = bool(db.execute(
            "SELECT 1 FROM follows WHERE follower_id=? AND following_id=?",
            (uid, user_id)).fetchone())

    profile = dict(user)
    profile.update({
        "posts"       : posts,
        "replies"     : replies,
        "followers"   : followers,
        "following"   : following,
        "is_following": is_following
    })
    return jsonify(profile), 200

@app.route("/api/users/me/update", methods=["PUT"])
@jwt_required()
def update_profile():
    uid  = get_jwt_identity()
    data = request.get_json()
    old_password = data.get("old_password")
    new_username = (data.get("username") or "").strip()
    new_email    = (data.get("email")    or "").strip().lower()
    new_password =  data.get("new_password")
    new_bio      = data.get("bio")

    with get_db() as db:
        user = db.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        if not check_password_hash(user["password"], old_password or ""):
            return jsonify({"error": "Password lama salah."}), 401

        updates = []
        params  = []
        if new_username:
            updates.append("username=?"); params.append(new_username)
        if new_email:
            updates.append("email=?");    params.append(new_email)
        if new_bio is not None:
            updates.append("bio=?");      params.append(new_bio)
        if new_password:
            if len(new_password) < 8:
                return jsonify({"error": "Password baru minimal 8 karakter."}), 400
            updates.append("password=?"); params.append(generate_password_hash(new_password))

        if not updates:
            return jsonify({"message": "Tidak ada perubahan."}), 200

        params.append(uid)
        try:
            db.execute(f"UPDATE users SET {', '.join(updates)} WHERE id=?", params)
        except sqlite3.IntegrityError:
            return jsonify({"error": "Username atau email sudah dipakai."}), 409

    return jsonify({"message": "Profil berhasil diperbarui!"}), 200

@app.route("/api/users/me/delete", methods=["DELETE"])
@jwt_required()
def delete_account():
    uid  = get_jwt_identity()
    data = request.get_json()
    with get_db() as db:
        user = db.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        if not check_password_hash(user["password"], data.get("password") or ""):
            return jsonify({"error": "Password salah. Konfirmasi gagal."}), 401
        db.execute("DELETE FROM users WHERE id=?", (uid,))
    return jsonify({"message": "Akun berhasil dihapus secara permanen."}), 200

@app.route("/api/users/<user_id>/follow", methods=["POST"])
@jwt_required()
def toggle_follow(user_id):
    uid = get_jwt_identity()
    if uid == user_id:
        return jsonify({"error": "Tidak bisa follow diri sendiri."}), 400

    with get_db() as db:
        existing = db.execute(
            "SELECT 1 FROM follows WHERE follower_id=? AND following_id=?",
            (uid, user_id)).fetchone()
        if existing:
            db.execute(
                "DELETE FROM follows WHERE follower_id=? AND following_id=?",
                (uid, user_id))
            following = False
        else:
            db.execute(
                "INSERT INTO follows (follower_id,following_id) VALUES (?,?)",
                (uid, user_id))
            following = True
            create_notification(db, user_id, uid, "follow", ref_id=uid)

        followers_count = db.execute(
            "SELECT COUNT(*) FROM follows WHERE following_id=?", (user_id,)).fetchone()[0]

    return jsonify({"following": following, "followers": followers_count}), 200


# ═══════════════════════════════════════════════════════════
# BOOKMARK ENDPOINTS
# ═══════════════════════════════════════════════════════════

@app.route("/api/posts/<post_id>/bookmark", methods=["POST"])
@jwt_required()
def toggle_bookmark(post_id):
    uid = get_jwt_identity()
    with get_db() as db:
        existing = db.execute(
            "SELECT 1 FROM bookmarks WHERE user_id=? AND post_id=?", (uid, post_id)).fetchone()
        if existing:
            db.execute("DELETE FROM bookmarks WHERE user_id=? AND post_id=?", (uid, post_id))
            bookmarked = False
        else:
            db.execute("INSERT INTO bookmarks (user_id,post_id) VALUES (?,?)", (uid, post_id))
            bookmarked = True
    return jsonify({"bookmarked": bookmarked}), 200

@app.route("/api/posts/bookmarks", methods=["GET"])
@jwt_required()
def get_bookmarks():
    uid = get_jwt_identity()
    with get_db() as db:
        rows = db.execute("""
            SELECT p.* FROM posts p
            JOIN bookmarks b ON b.post_id = p.id
            WHERE b.user_id = ?
            ORDER BY b.created_at DESC
        """, (uid,)).fetchall()
        posts = [enrich_post(dict(r), uid, db) for r in rows]
    return jsonify({"posts": posts}), 200


# ═══════════════════════════════════════════════════════════
# ANONYMOUS FEED
# ═══════════════════════════════════════════════════════════

@app.route("/api/posts/anonymous", methods=["GET"])
@jwt_required()
def anonymous_feed():
    uid   = get_jwt_identity()
    page  = int(request.args.get("page", 1))
    limit = 20
    offset = (page - 1) * limit
    with get_db() as db:
        rows = db.execute("""
            SELECT * FROM posts
            WHERE is_anonymous=1 AND parent_id IS NULL
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset)).fetchall()
        posts = [enrich_post(dict(r), uid, db) for r in rows]
    return jsonify({"posts": posts}), 200


# ═══════════════════════════════════════════════════════════
# NOTIFICATION ENDPOINTS
# ═══════════════════════════════════════════════════════════

@app.route("/api/notifications", methods=["GET"])
@jwt_required()
def get_notifications():
    uid   = get_jwt_identity()
    type_ = request.args.get("type", "all")
    with get_db() as db:
        base_q = """
            SELECT n.*, u.username as actor_username, u.avatar_url as actor_avatar
            FROM notifications n
            JOIN users u ON u.id = n.actor_id
            WHERE n.user_id=?
        """
        if type_ != "all":
            rows = db.execute(base_q + " AND n.type=? ORDER BY n.created_at DESC LIMIT 50",
                              (uid, type_)).fetchall()
        else:
            rows = db.execute(base_q + " ORDER BY n.created_at DESC LIMIT 50",
                              (uid,)).fetchall()

        unread = db.execute(
            "SELECT COUNT(*) FROM notifications WHERE user_id=? AND is_read=0",
            (uid,)).fetchone()[0]

    return jsonify({
        "notifications": [dict(r) for r in rows],
        "unread_count" : unread
    }), 200

@app.route("/api/notifications/unread-count", methods=["GET"])
@jwt_required()
def notif_unread_count():
    uid = get_jwt_identity()
    with get_db() as db:
        count = db.execute(
            "SELECT COUNT(*) FROM notifications WHERE user_id=? AND is_read=0",
            (uid,)).fetchone()[0]
        dm_count = db.execute("""
            SELECT COUNT(*) FROM dm_messages m
            JOIN dm_conversations c ON c.id = m.conv_id
            WHERE (c.user1_id=? OR c.user2_id=?) AND m.sender_id!=? AND m.is_read=0
        """, (uid, uid, uid)).fetchone()[0]
    return jsonify({"notifications": count, "messages": dm_count}), 200

@app.route("/api/notifications/read-all", methods=["POST"])
@jwt_required()
def read_all_notifications():
    uid = get_jwt_identity()
    with get_db() as db:
        db.execute("UPDATE notifications SET is_read=1 WHERE user_id=?", (uid,))
    return jsonify({"message": "Semua notifikasi ditandai dibaca."}), 200

def create_notification(db, user_id, actor_id, notif_type, ref_id=None, preview=None):
    if user_id == actor_id:
        return
    nid = uuid.uuid4().hex
    db.execute(
        "INSERT INTO notifications (id,user_id,actor_id,type,ref_id,preview) VALUES (?,?,?,?,?,?)",
        (nid, user_id, actor_id, notif_type, ref_id, preview)
    )


# ═══════════════════════════════════════════════════════════
# STORY ENDPOINTS
# ═══════════════════════════════════════════════════════════

@app.route("/api/stories", methods=["GET"])
@jwt_required()
def get_stories():
    uid = get_jwt_identity()
    with get_db() as db:
        rows = db.execute("""
            SELECT s.*, u.username, u.avatar_url,
                   EXISTS(SELECT 1 FROM story_views sv
                          WHERE sv.story_id=s.id AND sv.user_id=?) as viewed
            FROM stories s
            JOIN users u ON u.id = s.user_id
            WHERE s.expires_at > datetime('now')
            ORDER BY viewed ASC, s.created_at DESC
        """, (uid,)).fetchall()
    return jsonify({"stories": [dict(r) for r in rows]}), 200

@app.route("/api/stories/<story_id>/view", methods=["POST"])
@jwt_required()
def view_story(story_id):
    uid = get_jwt_identity()
    with get_db() as db:
        db.execute(
            "INSERT OR IGNORE INTO story_views (story_id,user_id) VALUES (?,?)",
            (story_id, uid))
    return jsonify({"ok": True}), 200

@app.route("/api/stories", methods=["POST"])
@jwt_required()
def create_story():
    uid = get_jwt_identity()
    if "media" not in request.files:
        return jsonify({"error": "File media diperlukan."}), 400

    f = request.files["media"]
    allowed = ALLOWED_IMG | ALLOWED_VID
    url_path, abs_path, err = save_upload(f, allowed, subfolder="stories")
    if err:
        return jsonify({"error": err}), 400

    media_type = "video" if allowed_file(f.filename, ALLOWED_VID) else "image"
    caption    = request.form.get("caption", "")
    sid        = uuid.uuid4().hex
    now        = datetime.now(WIB)
    expires    = (now + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    created    = now.strftime("%Y-%m-%d %H:%M:%S")

    with get_db() as db:
        db.execute(
            "INSERT INTO stories (id,user_id,media_url,media_type,caption,expires_at,created_at) VALUES (?,?,?,?,?,?,?)",
            (sid, uid, url_path, media_type, caption, expires, created)
        )
    return jsonify({"message": "Story berhasil diupload!", "story_id": sid}), 201


# ═══════════════════════════════════════════════════════════
# DM ENDPOINTS
# ═══════════════════════════════════════════════════════════

@app.route("/api/dm/conversations", methods=["GET"])
@jwt_required()
def get_conversations():
    uid = get_jwt_identity()
    with get_db() as db:
        rows = db.execute("""
            SELECT c.*,
                   CASE WHEN c.user1_id=? THEN c.user2_id ELSE c.user1_id END as partner_id,
                   u.username as partner_name,
                   u.avatar_url as partner_avatar,
                   (SELECT content FROM dm_messages
                    WHERE conv_id=c.id ORDER BY created_at DESC LIMIT 1) as last_message,
                   (SELECT created_at FROM dm_messages
                    WHERE conv_id=c.id ORDER BY created_at DESC LIMIT 1) as updated_at,
                   (SELECT COUNT(*) FROM dm_messages
                    WHERE conv_id=c.id AND sender_id!=? AND is_read=0) as unread_count
            FROM dm_conversations c
            JOIN users u ON u.id =
                CASE WHEN c.user1_id=? THEN c.user2_id ELSE c.user1_id END
            WHERE c.user1_id=? OR c.user2_id=?
            ORDER BY updated_at DESC NULLS LAST, c.created_at DESC
        """, (uid, uid, uid, uid, uid)).fetchall()
    return jsonify({"conversations": [dict(r) for r in rows]}), 200

@app.route("/api/dm/conversations", methods=["POST"])
@jwt_required()
def create_conversation():
    uid        = get_jwt_identity()
    data       = request.get_json()
    partner_id = data.get("partner_id")
    conv_type  = data.get("type", "dm")

    if not partner_id:
        return jsonify({"error": "partner_id diperlukan."}), 400
    if uid == partner_id:
        return jsonify({"error": "Tidak bisa DM diri sendiri."}), 400

    with get_db() as db:
        existing = db.execute("""
            SELECT id FROM dm_conversations
            WHERE (user1_id=? AND user2_id=?) OR (user1_id=? AND user2_id=?)
        """, (uid, partner_id, partner_id, uid)).fetchone()

        if existing:
            return jsonify({"conversation_id": existing["id"]}), 200

        cid = uuid.uuid4().hex
        db.execute(
            "INSERT INTO dm_conversations (id,user1_id,user2_id,type) VALUES (?,?,?,?)",
            (cid, uid, partner_id, conv_type)
        )
    return jsonify({"conversation_id": cid}), 201

@app.route("/api/dm/conversations/<conv_id>/messages", methods=["GET"])
@jwt_required()
def get_messages(conv_id):
    uid = get_jwt_identity()
    with get_db() as db:
        conv = db.execute(
            "SELECT * FROM dm_conversations WHERE id=? AND (user1_id=? OR user2_id=?)",
            (conv_id, uid, uid)).fetchone()
        if not conv:
            return jsonify({"error": "Conversation tidak ditemukan."}), 404

        rows = db.execute("""
            SELECT m.id, m.conv_id, m.sender_id, m.content,
                   m.reply_to_id, m.reply_to_content, m.reply_to_sender,
                   m.is_read, m.created_at,
                   u.username as sender_name, u.avatar_url as sender_avatar
            FROM dm_messages m
            JOIN users u ON u.id = m.sender_id
            WHERE m.conv_id=?
            ORDER BY m.created_at ASC
        """, (conv_id,)).fetchall()

        db.execute(
            "UPDATE dm_messages SET is_read=1 WHERE conv_id=? AND sender_id!=? AND is_read=0",
            (conv_id, uid))

    return jsonify({"messages": [dict(r) for r in rows]}), 200

@app.route("/api/dm/conversations/<conv_id>/messages", methods=["POST"])
@jwt_required()
def send_message(conv_id):
    uid  = get_jwt_identity()
    data = request.get_json()
    content          = (data.get("content") or "").strip()
    reply_to_id      = data.get("reply_to_id")
    reply_to_content = data.get("reply_to_content")
    reply_to_sender  = data.get("reply_to_sender")

    if not content:
        return jsonify({"error": "Pesan tidak boleh kosong."}), 400

    with get_db() as db:
        conv = db.execute(
            "SELECT * FROM dm_conversations WHERE id=? AND (user1_id=? OR user2_id=?)",
            (conv_id, uid, uid)).fetchone()
        if not conv:
            return jsonify({"error": "Conversation tidak ditemukan."}), 404

        mid = uuid.uuid4().hex
        db.execute("""
            INSERT INTO dm_messages
            (id,conv_id,sender_id,content,reply_to_id,reply_to_content,reply_to_sender,created_at)
            VALUES (?,?,?,?,?,?,?,?)
        """, (mid, conv_id, uid, content, reply_to_id, reply_to_content, reply_to_sender, now_wib()))
    return jsonify({"message_id": mid}), 201


# ═══════════════════════════════════════════════════════════
# AVATAR UPLOAD
# ═══════════════════════════════════════════════════════════

@app.route("/api/users/me/avatar", methods=["POST"])
@jwt_required()
def upload_avatar():
    uid = get_jwt_identity()
    if "avatar" not in request.files:
        return jsonify({"error": "File avatar diperlukan."}), 400
    f = request.files["avatar"]
    url_path, _, err = save_upload(f, ALLOWED_IMG, subfolder="avatars")
    if err:
        return jsonify({"error": err}), 400
    with get_db() as db:
        db.execute("UPDATE users SET avatar_url=? WHERE id=?", (url_path, uid))
    return jsonify({"avatar_url": url_path}), 200


# ═══════════════════════════════════════════════════════════
# KONSULTASI ENDPOINTS
# ═══════════════════════════════════════════════════════════

@app.route("/api/konsultasi/psikolog", methods=["GET"])
@jwt_required()
def get_psikolog():
    spec = request.args.get("spec", "semua")
    with get_db() as db:
        if spec == "semua":
            rows = db.execute("""
                SELECT p.*, u.avatar_url as avatar
                FROM psikolog_profiles p
                JOIN users u ON u.id = p.user_id
                WHERE p.available=1
                ORDER BY p.rating DESC
            """).fetchall()
        else:
            rows = db.execute("""
                SELECT p.*, u.avatar_url as avatar
                FROM psikolog_profiles p
                JOIN users u ON u.id = p.user_id
                WHERE p.available=1 AND LOWER(p.specialization) LIKE ?
                ORDER BY p.rating DESC
            """, (f"%{spec}%",)).fetchall()

    if not rows:
        dummy = [
            {"id":"p1","user_id":"sys1","name":"Dr. Anisa Rahayu, M.Psi","specialization":"Depresi & Kecemasan","bio":"Psikolog klinis berpengalaman dengan pendekatan CBT yang hangat dan empatik.","experience":8,"rating":4.9,"session_count":320,"price":150000,"available":1,"avatar":None},
            {"id":"p2","user_id":"sys2","name":"Dr. Sarah Putri, M.Psi","specialization":"Hubungan & Keluarga","bio":"Spesialis konseling hubungan dan dinamika keluarga dengan pendekatan sistemik.","experience":6,"rating":4.8,"session_count":215,"price":120000,"available":1,"avatar":None},
            {"id":"p3","user_id":"sys3","name":"Dr. Maya Sari, M.Psi","specialization":"Trauma & PTSD","bio":"Ahli trauma dengan sertifikasi EMDR internasional, pendekatan trauma-informed care.","experience":10,"rating":5.0,"session_count":480,"price":200000,"available":1,"avatar":None},
            {"id":"p4","user_id":"sys4","name":"Dr. Rina Dewi, M.Psi","specialization":"Karir & Stres","bio":"Konselor karir dan manajemen stres untuk profesional muda.","experience":5,"rating":4.7,"session_count":180,"price":100000,"available":1,"avatar":None},
        ]
        return jsonify({"psikolog": dummy}), 200

    return jsonify({"psikolog": [dict(r) for r in rows]}), 200

@app.route("/api/konsultasi/booking", methods=["POST"])
@jwt_required()
def booking_sesi():
    uid  = get_jwt_identity()
    data = request.get_json()

    psikolog_id = data.get("psikolog_id")
    date        = data.get("date")
    time_slot   = data.get("time")
    topic       = (data.get("topic") or "").strip()
    sesi_type   = data.get("type", "chat")
    psikolog_name = data.get("psikolog_name", "Psikolog")

    if not all([psikolog_id, date, time_slot, topic]):
        return jsonify({"error": "Tanggal, waktu, dan topik wajib diisi."}), 400

    sid = uuid.uuid4().hex
    with get_db() as db:
        db.execute("""
            INSERT INTO konsultasi_sessions
            (id, psikolog_id, user_id, date, time, topic, type, status, created_at)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (sid, psikolog_id, uid, date, time_slot, topic, sesi_type, "scheduled", now_wib()))

    return jsonify({
        "message"    : f"Booking dengan {psikolog_name} berhasil! 🎉",
        "session_id" : sid
    }), 201

@app.route("/api/konsultasi/sessions", methods=["GET"])
@jwt_required()
def get_sessions():
    uid = get_jwt_identity()
    with get_db() as db:
        rows = db.execute("""
            SELECT s.*,
                   COALESCE(p.name, u.username) as psikolog_name
            FROM konsultasi_sessions s
            LEFT JOIN psikolog_profiles p ON p.user_id = s.psikolog_id
            LEFT JOIN users u ON u.id = s.psikolog_id
            WHERE s.user_id=?
            ORDER BY s.date DESC, s.time DESC
        """, (uid,)).fetchall()
    return jsonify({"sessions": [dict(r) for r in rows]}), 200


# ═══════════════════════════════════════════════════════════
# POLL ENDPOINTS
# ═══════════════════════════════════════════════════════════

@app.route("/api/posts/with-poll", methods=["POST"])
@jwt_required()
def create_post_with_poll():
    uid      = get_jwt_identity()
    content  = (request.form.get("content") or "").strip()
    question = (request.form.get("poll_question") or "").strip()
    options  = request.form.getlist("poll_options")
    duration = int(request.form.get("poll_duration_hours", 24))
    is_anon  = request.form.get("is_anonymous", "0") == "1"

    if not content:
        return jsonify({"error": "Konten tidak boleh kosong."}), 400
    if not question:
        return jsonify({"error": "Pertanyaan poll wajib diisi."}), 400
    if len(options) < 2:
        return jsonify({"error": "Poll butuh minimal 2 pilihan."}), 400
    if len(options) > 4:
        return jsonify({"error": "Maksimal 4 pilihan poll."}), 400

    pid     = uuid.uuid4().hex
    poll_id = uuid.uuid4().hex
    ends_at = (datetime.now(WIB) + timedelta(hours=duration)).strftime("%Y-%m-%d %H:%M:%S")

    with get_db() as db:
        db.execute(
            "INSERT INTO posts (id,user_id,content,is_anonymous,created_at) VALUES (?,?,?,?,?)",
            (pid, uid, content, 1 if is_anon else 0, now_wib())
        )
        db.execute(
            "INSERT INTO polls (id,post_id,question,ends_at,created_at) VALUES (?,?,?,?,?)",
            (poll_id, pid, question, ends_at, now_wib())
        )
        for label in options:
            if label.strip():
                db.execute(
                    "INSERT INTO poll_options (id,poll_id,label) VALUES (?,?,?)",
                    (uuid.uuid4().hex, poll_id, label.strip())
                )
    return jsonify({"message": "Post dengan poll berhasil dibuat!", "post_id": pid}), 201

@app.route("/api/polls/<poll_id>/vote", methods=["POST"])
@jwt_required()
def vote_poll(poll_id):
    uid       = get_jwt_identity()
    data      = request.get_json()
    option_id = data.get("option_id")
    if not option_id:
        return jsonify({"error": "Pilih salah satu opsi."}), 400

    with get_db() as db:
        poll = db.execute("SELECT * FROM polls WHERE id=?", (poll_id,)).fetchone()
        if not poll:
            return jsonify({"error": "Poll tidak ditemukan."}), 404
        if poll["ends_at"] < now_wib():
            return jsonify({"error": "Poll sudah berakhir."}), 400

        existing = db.execute(
            "SELECT option_id FROM poll_votes WHERE user_id=? AND poll_id=?",
            (uid, poll_id)).fetchone()
        if existing:
            db.execute(
                "UPDATE poll_votes SET option_id=?, voted_at=? WHERE user_id=? AND poll_id=?",
                (option_id, now_wib(), uid, poll_id))
        else:
            db.execute(
                "INSERT INTO poll_votes (user_id,poll_id,option_id,voted_at) VALUES (?,?,?,?)",
                (uid, poll_id, option_id, now_wib()))

        results = db.execute("""
            SELECT o.id, o.label, COUNT(v.option_id) as votes
            FROM poll_options o
            LEFT JOIN poll_votes v ON v.option_id = o.id
            WHERE o.poll_id=?
            GROUP BY o.id
        """, (poll_id,)).fetchall()
        total = sum(r["votes"] for r in results)

    return jsonify({
        "voted"    : option_id,
        "results"  : [{"id":r["id"],"label":r["label"],"votes":r["votes"],
                        "percent": round(r["votes"]/total*100) if total else 0}
                       for r in results],
        "total"    : total
    }), 200

@app.route("/api/polls/<poll_id>", methods=["GET"])
@jwt_required()
def get_poll(poll_id):
    uid = get_jwt_identity()
    with get_db() as db:
        poll = db.execute("SELECT * FROM polls WHERE id=?", (poll_id,)).fetchone()
        if not poll:
            return jsonify({"error": "Poll tidak ditemukan."}), 404

        options = db.execute("""
            SELECT o.id, o.label, COUNT(v.option_id) as votes
            FROM poll_options o
            LEFT JOIN poll_votes v ON v.option_id = o.id
            WHERE o.poll_id=?
            GROUP BY o.id
        """, (poll_id,)).fetchall()

        my_vote = db.execute(
            "SELECT option_id FROM poll_votes WHERE user_id=? AND poll_id=?",
            (uid, poll_id)).fetchone()

        total = sum(r["votes"] for r in options)
        is_ended = poll["ends_at"] < now_wib()

    return jsonify({
        "id"      : poll["id"],
        "question": poll["question"],
        "ends_at" : poll["ends_at"],
        "is_ended": is_ended,
        "my_vote" : my_vote["option_id"] if my_vote else None,
        "total"   : total,
        "options" : [{"id":o["id"],"label":o["label"],"votes":o["votes"],
                       "percent": round(o["votes"]/total*100) if total else 0}
                      for o in options]
    }), 200


# ═══════════════════════════════════════════════════════════
# PIN POST ENDPOINTS
# ═══════════════════════════════════════════════════════════

@app.route("/api/posts/<post_id>/pin", methods=["POST"])
@jwt_required()
def toggle_pin(post_id):
    uid = get_jwt_identity()
    with get_db() as db:
        post = db.execute(
            "SELECT user_id FROM posts WHERE id=?", (post_id,)).fetchone()
        if not post or post["user_id"] != uid:
            return jsonify({"error": "Kamu hanya bisa pin postinganmu sendiri."}), 403

        existing = db.execute(
            "SELECT 1 FROM pinned_posts WHERE user_id=? AND post_id=?",
            (uid, post_id)).fetchone()
        if existing:
            db.execute("DELETE FROM pinned_posts WHERE user_id=? AND post_id=?", (uid, post_id))
            pinned = False
        else:
            db.execute("DELETE FROM pinned_posts WHERE user_id=?", (uid,))
            db.execute("INSERT INTO pinned_posts (user_id,post_id) VALUES (?,?)", (uid, post_id))
            pinned = True

    return jsonify({"pinned": pinned,
                    "message": "Postingan di-pin!" if pinned else "Pin dilepas."}), 200

@app.route("/api/users/<user_id>/pinned", methods=["GET"])
@jwt_required()
def get_pinned_post(user_id):
    uid = get_jwt_identity()
    with get_db() as db:
        row = db.execute("""
            SELECT p.* FROM posts p
            JOIN pinned_posts pp ON pp.post_id = p.id
            WHERE pp.user_id=?
        """, (user_id,)).fetchone()
        if not row:
            return jsonify({"post": None}), 200
        post = enrich_post(dict(row), uid, db)
    return jsonify({"post": post}), 200


# ─────────────────────────────────────────────
# ENTRYPOINT
# ─────────────────────────────────────────────
init_db()
if __name__ == "__main__":
    print("🌸  Womenspace API running → https://womenspace.onrender.com/api")
    app.run(debug=True, port=5000)