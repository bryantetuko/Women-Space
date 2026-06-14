"""
╔══════════════════════════════════════════════════════════╗
║   check_model.py — Cek label mapping & test model .pkl  ║
║   Jalankan ini SEBELUM menjalankan app.py                ║
╚══════════════════════════════════════════════════════════╝

Cara pakai:
  python check_model.py
  python check_model.py --image foto_wajah.jpg
"""

import os, sys, argparse
import numpy as np
import warnings

# Suppress sklearn version mismatch warning (PCA trained on older sklearn)
try:
    from sklearn.exceptions import InconsistentVersionWarning
    warnings.filterwarnings("ignore", category=InconsistentVersionWarning)
except ImportError:
    pass

# ─────────────────────────────────────────────────────────
# KONFIGURASI — sesuaikan ini dengan training kamu!
# ─────────────────────────────────────────────────────────
IMG_SIZE    = 128     # ✅ confirmed: n_features=16384 → sqrt=128
LABEL_MAP   = {0: "male", 1: "female"}   # ✅ confirmed dari Colab: pred==1 → WANITA
MODEL_FILE  = "gender_model.pkl"
PCA_FILE    = "pca_model.pkl"
CASCADE     = "haarcascade_frontalface_default.xml"
# ─────────────────────────────────────────────────────────

def check():
    print("=" * 55)
    print("  WOMENSPACE — Model Checker")
    print("=" * 55)

    # 1. Cek joblib
    try:
        import joblib
        print("✅  joblib          : OK")
    except ImportError:
        print("❌  joblib          : NOT INSTALLED  →  pip install joblib")
        return

    # 2. Cek cv2
    try:
        import cv2
        print(f"✅  opencv          : {cv2.__version__}")
    except ImportError:
        print("❌  opencv          : NOT INSTALLED  →  pip install opencv-python-headless")
        return

    # 3. Cek xgboost
    try:
        import xgboost as xgb
        print(f"✅  xgboost         : {xgb.__version__}")
    except ImportError:
        print("❌  xgboost         : NOT INSTALLED  →  pip install xgboost")

    # 4. Load gender model
    if not os.path.exists(MODEL_FILE):
        print(f"❌  {MODEL_FILE} : FILE TIDAK ADA di {os.getcwd()}")
        return

    model = joblib.load(MODEL_FILE)
    print(f"✅  {MODEL_FILE} : loaded")
    print(f"   Type   : {type(model).__name__}")

    # 5. Cek classes_
    if hasattr(model, "classes_"):
        print(f"   classes_: {model.classes_}")
        print()
        print("   ── LABEL MAPPING yang akan dipakai di app.py ──")
        for idx, cls in enumerate(model.classes_):
            meaning = LABEL_MAP.get(int(cls), "???")
            print(f"   class {cls}  →  '{meaning}'")
        print()
        print("   ⚠️  Kalau mapping terbalik (male↔female),")
        print("      edit LABEL_MAP di check_model.py DAN app.py!")
    else:
        print("   ⚠️  model tidak punya .classes_ — tidak bisa auto-detect label")

    # 6. Load PCA
    if os.path.exists(PCA_FILE):
        pca = joblib.load(PCA_FILE)
        print(f"✅  {PCA_FILE}    : loaded")
        print(f"   n_components : {pca.n_components_}")
        print(f"   n_features   : {pca.n_features_in_}  (harus = {IMG_SIZE*IMG_SIZE})")
        if pca.n_features_in_ != IMG_SIZE * IMG_SIZE:
            print(f"   ❌  MISMATCH! IMG_SIZE di app.py harus "
                  f"{int(pca.n_features_in_ ** 0.5)}, bukan {IMG_SIZE}")
    else:
        print(f"ℹ️   {PCA_FILE} tidak ada — PCA akan dilewati (OK kalau memang tidak pakai PCA)")

    # 7. Load cascade
    if not os.path.exists(CASCADE):
        print(f"❌  {CASCADE}")
        print("   Download dari:")
        print("   https://github.com/opencv/opencv/blob/master/data/haarcascades/haarcascade_frontalface_default.xml")
    else:
        cascade = cv2.CascadeClassifier(CASCADE)
        if cascade.empty():
            print(f"❌  {CASCADE} : file rusak / tidak valid")
        else:
            print(f"✅  {CASCADE} : OK")

    print()

    # 8. Test dummy prediction
    print("── Test dummy prediction ────────────────────────")
    dummy = np.zeros((1, IMG_SIZE * IMG_SIZE), dtype=np.float32)
    try:
        if os.path.exists(PCA_FILE):
            pca   = joblib.load(PCA_FILE)
            dummy = pca.transform(dummy)
        pred   = model.predict(dummy)[0]
        proba  = model.predict_proba(dummy)[0]
        label  = LABEL_MAP.get(int(pred), "unknown")
        print(f"   Dummy input shape : {dummy.shape}")
        print(f"   Prediction        : {pred}  →  '{label}'")
        print(f"   Probabilities     : {[round(p,4) for p in proba]}")
        print("   ✅  Model bisa dipanggil dengan benar")
    except Exception as e:
        print(f"   ❌  Predict gagal: {e}")

    print()


def test_image(image_path: str):
    """Test pipeline lengkap IDENTIK dengan Colab."""
    import cv2, joblib

    print(f"\n── Test dengan gambar: {image_path} ──")
    if not os.path.exists(image_path):
        print(f"❌  File tidak ditemukan: {image_path}")
        return

    model   = joblib.load(MODEL_FILE)
    cascade = cv2.CascadeClassifier(CASCADE)
    profile = cv2.CascadeClassifier("haarcascade_profileface.xml") \
              if os.path.exists("haarcascade_profileface.xml") else None
    pca     = joblib.load(PCA_FILE) if os.path.exists(PCA_FILE) else None

    img_bgr = cv2.imread(image_path)
    gray    = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # equalizeHist — SAMA seperti Colab
    gray_balanced = cv2.equalizeHist(gray)

    faces = cascade.detectMultiScale(gray_balanced, 1.1, 5, minSize=(40, 40))
    if len(faces) == 0 and profile:
        faces = profile.detectMultiScale(gray_balanced, 1.1, 5, minSize=(40, 40))

    print(f"   Wajah terdeteksi  : {len(faces)}")
    if len(faces) == 0:
        print("   ❌  Tidak ada wajah — coba foto lain")
        return

    x, y, w, h = max(faces, key=lambda f: f[2]*f[3])
    crop = cv2.resize(gray_balanced[y:y+h, x:x+w], (IMG_SIZE, IMG_SIZE))

    # Normalisasi /255.0 — SAMA seperti Colab
    feat = crop.flatten().reshape(1, -1).astype('float32') / 255.0

    if pca:
        feat = pca.transform(feat)

    pred   = int(model.predict(feat)[0])
    proba  = model.predict_proba(feat)[0]
    label  = LABEL_MAP.get(pred, "unknown")
    conf   = float(proba[pred])

    print(f"   Prediksi          : {pred} → '{label.upper()}'")
    print(f"   Confidence        : {conf*100:.1f}%")
    print(f"   Prob [pria, wanita]: {[round(p,4) for p in proba]}")
    print(f"   {'✅  Lolos — WANITA!' if label == 'female' else '🚫  Ditolak — PRIA'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", help="Path ke foto wajah untuk di-test", default=None)
    args = parser.parse_args()

    check()
    if args.image:
        test_image(args.image)
