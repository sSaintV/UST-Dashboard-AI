
import onnxruntime as ort
import numpy as np

session = ort.InferenceSession('C:/Users/genaiuser/Documents/UST Dashboard AI/backend/models/emotion-ferplus-8.onnx', providers=['CPUExecutionProvider'])
input_name = session.get_inputs()[0].name

def get_probs(img):
    logits = session.run(None, {input_name: img})[0][0]
    e = np.exp(logits - logits.max())
    return e / e.sum()

img_raw = np.random.uniform(0, 255, (1, 1, 64, 64)).astype(np.float32)
img_norm = (img_raw - img_raw.mean()) / (img_raw.std() + 1e-5)

print('Raw:', get_probs(img_raw))
print('Norm:', get_probs(img_norm))

