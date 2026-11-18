import io
import os
import time
import requests

API_BASE = os.getenv("RUBIKA_API_BASE", "https://botapi.rubika.ir/v3")

class RubikaError(RuntimeError):
    pass

def _call(method: str, payload: dict):
    token = os.environ["RUBIKA_BOT_TOKEN"]
    url = f"{API_BASE}/{token}/{method}"
    response = requests.post(url, json=payload, timeout=35)
    response.raise_for_status()
    body = response.json()
    if body.get("status") != "OK":
        raise RubikaError(f"Rubika {method} failed: {body}")
    return body.get("data", {})

def send_text(chat_id: str, text: str):
    return _call("sendMessage", {"chat_id": chat_id, "text": text})

def _shrink(image_path: str) -> bytes:
    """عکس بزرگ را کوچک و فشرده می‌کند (آپلود سریع‌تر از سرور گیتاب)."""
    try:
        from PIL import Image
        with Image.open(image_path) as img:
            img = img.convert("RGB")
            img.thumbnail((1280, 1280))
            buf = io.BytesIO()
            img.save(buf, "JPEG", quality=82, optimize=True)
            return buf.getvalue()
    except Exception as exc:
        print(f"shrink skipped: {exc}")
        with open(image_path, "rb") as f:
            return f.read()

def _upload(data: bytes, name: str) -> str:
    info = _call("requestSendFile", {"type": "Image"})
    upload_url = info.get("upload_url")
    if not upload_url:
        raise RubikaError(f"requestSendFile did not return upload_url: {info}")
    uploaded = requests.post(upload_url, files={"file": (name, data, "image/jpeg")},
                             timeout=(15, 120))
    uploaded.raise_for_status()
    body = uploaded.json()
    file_id = body.get("data", body).get("file_id")
    if not file_id:
        raise RubikaError(f"Image upload did not return file_id: {body}")
    return file_id

def send_image(chat_id: str, image_path: str, caption: str):
    data = _shrink(image_path)
    print(f"uploading image: {len(data) // 1024} KB")
    last = None
    for attempt in range(3):          # تا ۳ بار تلاش مجدد
        try:
            file_id = _upload(data, "photo.jpg")
            return _call("sendFile", {"chat_id": chat_id, "file_id": file_id,
                                      "type": "Image", "text": caption})
        except (requests.RequestException, RubikaError) as exc:
            last = exc
            print(f"upload attempt {attempt + 1} failed: {exc}")
            time.sleep(3)
    raise last
