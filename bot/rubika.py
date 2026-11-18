import os
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

def send_image(chat_id: str, image_path: str, caption: str):
    # Rubika file upload is a two-step process: requestSendFile -> upload -> sendFile.
    info = _call("requestSendFile", {"type": "Image"})
    upload_url = info.get("upload_url")
    if not upload_url:
        raise RubikaError(f"requestSendFile did not return upload_url: {info}")

    with open(image_path, "rb") as image_file:
        uploaded = requests.post(
            upload_url,
            files={"file": (os.path.basename(image_path), image_file, "image/jpeg")},
            timeout=90,
        )
    uploaded.raise_for_status()
    upload_body = uploaded.json()
    data = upload_body.get("data", upload_body)
    file_id = data.get("file_id")
    if not file_id:
        raise RubikaError(f"Image upload did not return file_id: {upload_body}")

    return _call("sendFile", {
        "chat_id": chat_id,
        "file_id": file_id,
        "type": "Image",
        "text": caption,
    })
