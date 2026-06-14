"""
test_register.py — Test register langsung ke backend tanpa browser
Jalankan: python test_register.py
Pastikan backend (app.py) sudah jalan dulu!
"""

import requests, os, sys

BASE = "http://localhost:5000/api"

# ── Ganti ini dengan path foto wajah perempuan kamu ──────
FOTO_PATH = r"D:\code\SOFENGMLHCI\backend\foto_cewe.jpg"   # ← GANTI INI
# ─────────────────────────────────────────────────────────

USERNAME = "testuser123"
EMAIL    = "test@womenspace.com"
PASSWORD = "password123"

print("=" * 55)
print("  WOMENSPACE — Register Test")
print("=" * 55)

# 1. Cek backend hidup
print("\n[1] Cek backend...")
try:
    r = requests.get(BASE.replace("/api", "/uploads/"), timeout=3)
    print(f"    ✅ Backend aktif")
except Exception as e:
    print(f"    ❌ Backend tidak bisa diakses: {e}")
    print("    → Pastikan 'python app.py' sudah dijalankan!")
    sys.exit(1)

# 2. Cek file foto ada
print(f"\n[2] Cek foto: {FOTO_PATH}")
if not os.path.exists(FOTO_PATH):
    print(f"    ❌ File tidak ditemukan!")
    print(f"    → Ganti FOTO_PATH di script ini dengan path foto yang benar")
    sys.exit(1)
print(f"    ✅ File ada ({os.path.getsize(FOTO_PATH)} bytes)")

# 3. Verify face
print(f"\n[3] POST /api/auth/verify-face ...")
try:
    with open(FOTO_PATH, "rb") as f:
        r = requests.post(
            f"{BASE}/auth/verify-face",
            files={"face_photo": (os.path.basename(FOTO_PATH), f, "image/jpeg")},
            timeout=30
        )
    print(f"    Status : {r.status_code}")
    print(f"    Response: {r.json()}")

    if r.status_code != 200 or not r.json().get("allowed"):
        print("    ❌ Verifikasi wajah gagal — tidak lanjut register")
        sys.exit(1)
    print("    ✅ Verifikasi wajah berhasil!")

except Exception as e:
    print(f"    ❌ Error: {e}")
    sys.exit(1)

# 4. Register
print(f"\n[4] POST /api/auth/register ...")
try:
    r = requests.post(
        f"{BASE}/auth/register",
        json={
            "username"   : USERNAME,
            "email"      : EMAIL,
            "password"   : PASSWORD,
            "ml_verified": True
        },
        headers={"Content-Type": "application/json"},
        timeout=10
    )
    print(f"    Status : {r.status_code}")
    print(f"    Response: {r.json()}")

    if r.status_code == 201:
        token = r.json().get("token")
        print(f"    ✅ REGISTER BERHASIL! Token: {token[:30]}...")
    elif r.status_code == 409:
        print(f"    ⚠️  Username/email sudah ada — coba username lain")
    else:
        print(f"    ❌ Register gagal")
        sys.exit(1)

except Exception as e:
    print(f"    ❌ Error: {e}")
    sys.exit(1)

# 5. Login test
print(f"\n[5] POST /api/auth/login ...")
try:
    r = requests.post(
        f"{BASE}/auth/login",
        json={"username": USERNAME, "password": PASSWORD},
        headers={"Content-Type": "application/json"},
        timeout=10
    )
    print(f"    Status : {r.status_code}")
    print(f"    Response: {r.json()}")

    if r.status_code == 200:
        print(f"    ✅ LOGIN BERHASIL!")
        print(f"\n{'='*55}")
        print(f"  Gunakan kredensial ini di browser:")
        print(f"  Username : {USERNAME}")
        print(f"  Password : {PASSWORD}")
        print(f"{'='*55}")
    else:
        print(f"    ❌ Login gagal padahal register berhasil — aneh!")

except Exception as e:
    print(f"    ❌ Error: {e}")

print("\n✅ Test selesai.")
