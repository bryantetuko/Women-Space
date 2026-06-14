import os
import numpy as np
from tensorflow.keras.models import load_model

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "gender_model.h5")

print("=" * 50)
print("WOMENSPACE — CNN Model Checker")
print("=" * 50)

model = load_model(MODEL_PATH, compile=False)

print("✅ gender_model.h5 loaded")
print("Input shape :", model.input_shape)
print("Output shape:", model.output_shape)

dummy = np.zeros((1, 64, 64, 1), dtype="float32")
pred = model.predict(dummy, verbose=0)

print("Dummy input shape:", dummy.shape)
print("Prediction:", pred)
print("✅ CNN bisa dipanggil")