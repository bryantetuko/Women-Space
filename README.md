# 🌸 Womenspace — Developer Guide

Exclusive forum platform for women with ML-based verification.

[![Figma](https://img.shields.io/badge/Figma-000000?style=for-the-badge&logo=figma&logoColor=white)](https://www.figma.com/design/d0WK2Cz18eQnyeN6N8BgRU/AoL-Software-Engineering?node-id=629-11229&t=hhbW0i3qc5zABoNi-1)

---

## 📁 Folder Structure

```
womenspace/
├── backend/
│   ├── app.py              ← Main Flask API (routing + DB)
│   ├── womenspace.db       ← SQLite (automatically created when running)
│   └── uploads/            ← File upload folder (automatically created)
│       ├── media/          ← Photos/videos/audio from posts
│       └── temp_faces/     ← Face photos during registration
│
└── frontend/
    ├── index.html          ← Single Page App
    ├── style.css           ← All styling
    └── app.js              ← All JS logic + API fetch
```

---

## 🗄️ Database Schema

```sql
users (id, username, email, password, avatar_url, bio, created_at)
follows (follower_id, following_id, created_at)
posts (id, user_id, content, media_url, media_type, parent_id, repost_of, created_at)
likes (user_id, post_id, created_at)
```

---

## ⚙️ Backend Setup

### 1. Install Python dependencies
```bash
pip install flask flask-cors flask-jwt-extended werkzeug pillow
```

### 2. Run the backend
```bash
cd backend
python app.py
```
Backend runs at: `http://localhost:5000`

The `womenspace.db` database is automatically created on the first run.

---

## 🌐 Frontend Setup

Open `frontend/index.html` directly in your browser, or serve it with:
```bash
cd frontend
python -m http.server 8080
```
Open: `http://localhost:8080`

> **Make sure CORS is enabled in Flask** (already configured in `app.py`).

---

## 🤖 ML Model Integration (IMPORTANT)

Your ML model is called at the `/api/auth/verify-face` endpoint in `app.py`.

Find the `TODO: REPLACE THIS BLOCK` comment block and replace it with your model code:

### Option A — Model in the same file (direct import)
```python
# At the top of app.py, add:
import your_ml_module as ml

# Inside the verify_face() function, replace the stub with:
result     = ml.predict_gender(tmp_path)   # path to the temporary image file
gender     = result["gender"]              # "male" or "female"
confidence = result["confidence"]          # 0.0 – 1.0
```

### Option B — Model as a separate microservice (FastAPI/another Flask app)
```python
import requests as req

res        = req.post("http://localhost:8001/predict",
                      files={"image": open(tmp_path, "rb")})
gender     = res.json()["gender"]
confidence = res.json()["confidence"]
```

### Expected model output format:
```python
{
  "gender"    : "female",   # atau "male"
  "confidence": 0.97        # nilai 0.0 hingga 1.0
}
```

---

## 🔌 API Endpoints

| Method | Endpoint                     | Keterangan                          | Auth? |
|--------|------------------------------|-------------------------------------|-------|
| POST   | /api/auth/verify-face        | Upload foto → verifikasi ML         | ❌    |
| POST   | /api/auth/register           | Daftar akun baru                    | ❌    |
| POST   | /api/auth/login              | Login → dapat JWT token             | ❌    |
| GET    | /api/auth/me                 | Info user yang login                | ✅    |
| GET    | /api/posts/fyp               | Feed For You (semua postingan)      | ✅    |
| GET    | /api/posts/following         | Feed dari akun yang di-follow       | ✅    |
| POST   | /api/posts                   | Buat postingan baru (multipart)     | ✅    |
| POST   | /api/posts/:id/like          | Toggle like/unlike                  | ✅    |
| POST   | /api/posts/:id/reply         | Balas postingan                     | ✅    |
| POST   | /api/posts/:id/repost        | Repost                              | ✅    |
| GET    | /api/posts/:id/replies       | Ambil semua replies                 | ✅    |
| GET    | /api/search?q=               | Cari postingan & user               | ✅    |
| GET    | /api/search/trending         | Postingan trending (7 hari)         | ✅    |
| GET    | /api/users/:id               | Profil user + postingan             | ✅    |
| PUT    | /api/users/me/update         | Edit profil (perlu old_password)    | ✅    |
| DELETE | /api/users/me/delete         | Hapus akun permanen                 | ✅    |
| POST   | /api/users/:id/follow        | Toggle follow/unfollow              | ✅    |

---

## 🔐 JWT Authentication

After login/register, save the `token` from the response.
Send it with every request as a header:
```
Authorization: Bearer <token>
```

The frontend handles this automatically via `localStorage`.

---

## 📈 Next Steps (Roadmap)

- [ ] Deploy backend ke Railway / Render / VPS
- [ ] Replace SQLite → PostgreSQL for production
- [ ] Add profile avatar uploads
- [ ] Real-time notifications (WebSocket / SSE)
- [ ] Rate limiting & stricter input sanitization
- [ ] HTTPS + environment variable for the JWT secret
