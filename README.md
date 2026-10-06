# 🌸 Womenspace — Developer Guide

Platform forum eksklusif perempuan dengan verifikasi ML.

---

## 📁 Struktur Folder

```
womenspace/
├── backend/
│   ├── app.py              ← Flask API utama (routing + DB)
│   ├── womenspace.db       ← SQLite (auto-dibuat saat run)
│   └── uploads/            ← folder file upload (auto-dibuat)
│       ├── media/          ← foto/video/audio dari postingan
│       └── temp_faces/     ← foto wajah saat registrasi
│
└── frontend/
    ├── index.html          ← Single Page App
    ├── style.css           ← Semua styling
    └── app.js              ← Semua logika JS + fetch API
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

## ⚙️ Setup Backend

### 1. Install dependensi Python
```bash
pip install flask flask-cors flask-jwt-extended werkzeug pillow
```

### 2. Jalankan backend
```bash
cd backend
python app.py
```
Backend berjalan di: `http://localhost:5000`

Database `womenspace.db` otomatis dibuat saat pertama kali run.

---

## 🌐 Setup Frontend

Buka `frontend/index.html` langsung di browser, atau serve dengan:
```bash
cd frontend
python -m http.server 8080
```
Buka: `http://localhost:8080`

> **Pastikan CORS di Flask sudah aktif** (sudah dikonfigurasi di `app.py`).

---

## 🤖 Integrasi Model ML (PENTING)

Model ML kamu dipanggil di endpoint `/api/auth/verify-face` dalam file `app.py`.

Cari blok komentar `TODO: REPLACE THIS BLOCK` dan ganti dengan kode model kamu:

### Opsi A — Model di file yang sama (import langsung)
```python
# Di bagian atas app.py, tambahkan:
import your_ml_module as ml

# Di dalam fungsi verify_face(), ganti stub dengan:
result     = ml.predict_gender(tmp_path)   # path ke file gambar sementara
gender     = result["gender"]              # "male" atau "female"
confidence = result["confidence"]          # 0.0 – 1.0
```

### Opsi B — Model sebagai microservice terpisah (FastAPI/Flask lain)
```python
import requests as req

res        = req.post("http://localhost:8001/predict",
                      files={"image": open(tmp_path, "rb")})
gender     = res.json()["gender"]
confidence = res.json()["confidence"]
```

### Format output yang diharapkan dari model kamu:
```python
{
  "gender"    : "female",   # atau "male"
  "confidence": 0.97        # nilai 0.0 hingga 1.0
}
```

---

## 🔌 Daftar API Endpoints

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

## 🔐 Autentikasi JWT

Setelah login/register, simpan `token` dari response.
Kirim di setiap request sebagai header:
```
Authorization: Bearer <token>
```

Frontend sudah menangani ini secara otomatis via `localStorage`.

---

## 📈 Langkah Selanjutnya (Roadmap)

- [ ] Deploy backend ke Railway / Render / VPS
- [ ] Ganti SQLite → PostgreSQL untuk production
- [ ] Tambah upload avatar di profil
- [ ] Notifikasi real-time (WebSocket / SSE)
- [ ] Rate limiting & input sanitization lebih ketat
- [ ] HTTPS + environment variable untuk JWT secret
