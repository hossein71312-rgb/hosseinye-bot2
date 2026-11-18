import os
import random
import tempfile

from bot import commons
from bot.places import PLACES, GENERIC
from bot.rubika import send_image
from bot.state import already_published, mark_published

CHAT_ID = os.environ["RUBIKA_CHANNEL_ID"]

def _caption(title, text, credit):
    head = f"🌿 {title}\n\n" if title else "🌿 "
    return f'{head}{text}\n\n#طبیعت_ایران #ایران_زیبا'

def _attempt(fetch):
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as t:
        path = t.name
    try:
        credit = fetch(path)
        return path, credit
    except Exception as exc:
        print(f"fetch failed: {exc}")
        return path, None

def publish_one(state):
    skip = lambda k: already_published(state, k)
    start = state.get("idx", 0)
    # ۱) مکان‌های منتخب با متن اختصاصی
    for step in range(min(len(PLACES), 4)):
        i = (start + step) % len(PLACES)
        place = PLACES[i]
        path, credit = _attempt(lambda p: commons.by_place(place["query"], p, skip))
        try:
            if credit:
                send_image(CHAT_ID, path, _caption(place["title"], place["desc"], credit))
                mark_published(state, credit["key"])
                state["idx"] = i + 1
                return True
        finally:
            _rm(path)
    state["idx"] = start + 4
    # ۲) پشتیبان: عکس تصادفی از دستهٔ طبیعت ایران با متن کلی
    path, credit = _attempt(lambda p: commons.by_category(p, skip))
    try:
        if credit:
            send_image(CHAT_ID, path, _caption("", random.choice(GENERIC), credit))
            mark_published(state, credit["key"])
            return True
    finally:
        _rm(path)
    return False

def _rm(path):
    try:
        os.unlink(path)
    except OSError:
        pass
