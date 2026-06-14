"""
cek_db.py — Cek koneksi database dan isi tabel Womenspace
Jalankan: python cek_db.py
Letakkan di folder backend/ (sama dengan app.py dan womenspace.db)
"""

import sqlite3, os

DB_PATH = "womenspace.db"

print("=" * 50)
print("  WOMENSPACE — Database Checker")
print("=" * 50)

# 1. Cek file database ada tidak
if not os.path.exists(DB_PATH):
    print(f"\n❌  File '{DB_PATH}' TIDAK ADA!")
    print("   → Jalankan app.py dulu agar database dibuat otomatis.")
    exit()

size = os.path.getsize(DB_PATH)
print(f"\n✅  File ditemukan : {DB_PATH}")
print(f"   Ukuran         : {size} bytes")

# 2. Coba koneksi
try:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    print("✅  Koneksi        : BERHASIL")
except Exception as e:
    print(f"❌  Koneksi GAGAL  : {e}")
    exit()

# 3. Cek tabel yang ada
tables = conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
).fetchall()

print(f"\n── Tabel ditemukan : {len(tables)} ──────────────────")
expected = {"users", "posts", "likes", "follows"}
found    = {t["name"] for t in tables}

for t in sorted(expected):
    status = "✅" if t in found else "❌  TIDAK ADA"
    print(f"   {status}  {t}")

missing = expected - found
if missing:
    print(f"\n⚠️  Tabel kurang: {missing}")
    print("   → Jalankan app.py lagi, init_db() akan membuat tabel yang hilang.")

# 4. Isi setiap tabel
print("\n── Jumlah data ─────────────────────────────────")
for t in sorted(found & expected):
    count = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print(f"   {t:10s} : {count} baris")

# 5. Tampilkan daftar user
print("\n── Daftar User ─────────────────────────────────")
users = conn.execute(
    "SELECT id, username, email, created_at FROM users ORDER BY created_at DESC"
).fetchall()

if not users:
    print("   (belum ada user yang terdaftar)")
    print("\n   ⚠️  Ini berarti proses register BELUM berhasil menyimpan ke DB.")
    print("   → Cek CORS dan pastikan POST /api/auth/register dapat 201.")
else:
    for u in users:
        print(f"   @{u['username']:<20} | {u['email']:<30} | {u['created_at']}")

# 6. Tampilkan 5 post terbaru
print("\n── 5 Post Terbaru ──────────────────────────────")
posts = conn.execute(
    "SELECT p.content, u.username, p.created_at FROM posts p "
    "JOIN users u ON p.user_id = u.id "
    "ORDER BY p.created_at DESC LIMIT 5"
).fetchall()

if not posts:
    print("   (belum ada postingan)")
else:
    for p in posts:
        preview = p["content"][:50] + "..." if len(p["content"]) > 50 else p["content"]
        print(f"   @{p['username']}: {preview}")

conn.close()
print("\n✅  Pengecekan selesai.")
print("=" * 50)
