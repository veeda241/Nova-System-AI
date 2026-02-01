import os
import requests

def download_file(url, path):
    print(f"Downloading {url} to {path}...")
    response = requests.get(url, stream=True)
    response.raise_for_status()
    with open(path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    print("Done.")

models_dir = os.path.join("models", "piper")
os.makedirs(models_dir, exist_ok=True)

onnx_url = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/low/en_US-lessac-low.onnx"
json_url = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/low/en_US-lessac-low.onnx.json"

download_file(onnx_url, os.path.join(models_dir, "en_US-lessac-low.onnx"))
download_file(json_url, os.path.join(models_dir, "en_US-lessac-low.onnx.json"))
