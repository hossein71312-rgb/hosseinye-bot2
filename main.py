import os
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import jdatetime

from bot.content import ADHKAR, DUAS, OCCASIONS
import tempfile
from bot import commons
from bot.card import make_card
from bot.places import PLACES
from bot.rubika import send_text, send_image
from bot.state import load_state, save_state, done, mark
from bot.times import get_day, settings, HIJRI_MONTHS

TZ = ZoneInfo("Asia/Tehran")
CHAT_ID = os.environ["RUBIKA_CHANNEL_ID"]
HANDLE = os.getenv("CHANNEL_HANDLE", "").strip()
LATE = 900      # حداکثر تأخیر مجاز (ثانیه)؛ بعد از آن پست آن نوبت رد می‌شود
EARLY = 120     # ارسال زودتر برای نوبت‌های غیر اذان
SLEEP_MAX = 660 # برای اذان تا ۱۱ دقیقه صبر می‌کند تا دقیقاً سر وقت بفرستد

PRAYERS = [("Fajr", "اذان صبح"), ("Dhuhr", "اذان ظهر"), ("Maghrib", "اذان مغرب")]
WEEKDAYS = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]
SHAMSI = ["", "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
          "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]

def now_tehran():
    return datetime.now(TZ)

def fa(n):
    return str(n).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))

def date_line(day, hijri):
    j = jdatetime.date.fromgregorian(date=day)
    m, d, y = hijri
    return f"📅 {fa(j.day)} {SHAMSI[j.month]} {fa(j.year)} | {fa(d)} {HIJRI_MONTHS[m]} {fa(y)}"

def at(now, hhmm):
    h, m = map(int, hhmm.split(":"))
    return now.replace(hour=h, minute=m, second=0, microsecond=0)

def fetch_photo(state):
    """عکس یک مسجد یا حرم؛ اگر پیدا نشد None (پست بدون عکس ارسال می‌شود)."""
    start = state.get("pi", 0)
    for attempt in (lambda k: done(state, k), lambda k: False):   # بار دوم تکراری هم مجاز است
        for step in range(5):
            title, query = PLACES[(start + step) % len(PLACES)]
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as t:
                path = t.name
            try:
                credit = commons.by_place(query, path, attempt)
            except Exception as exc:
                print(f"photo failed ({query}): {exc}")
                credit = None
            if credit:
                state["pi"] = (start + step + 1) % len(PLACES)
                return {"path": path, "key": credit["key"], "line": f'📍 {title}'}
            os.unlink(path)
    return None

def post(state, key, text, photo=None):
    try:
        sent = False
        if photo:
            try:
                send_image(CHAT_ID, photo["path"], f'{text}\n\n{photo["line"]}')
                mark(state, photo["key"])
                sent = True
            except Exception as exc:
                print(f"image send failed, sending text only: {exc}")
        if not sent:
            send_text(CHAT_ID, text)
    finally:
        if photo:
            try:
                os.unlink(photo["path"])
            except OSError:
                pass
    mark(state, key)
    print(f"posted {key}")

def post_card(state, key, day, hijri):
    j = jdatetime.date.fromgregorian(date=day)
    path = make_card(WEEKDAYS[day.weekday()], day.strftime("%A"), j.day, SHAMSI[j.month],
                     day.strftime("%Y   %b   %d").replace("  0", "  "),
                     f"{hijri[1]:02d} {HIJRI_MONTHS[hijri[0]]} {hijri[2]}", HANDLE, friday=day.weekday() == 4)
    try:
        send_image(CHAT_ID, path, "")
    finally:
        os.unlink(path)
    mark(state, key)
    print(f"posted {key}")

def pick(items, day, offset=0):
    return items[(day.toordinal() + offset) % len(items)]

def dhikr_text(title, item, tag):
    return f"{title}\n\n{item[0]}\n\n{item[1]}\n\n{tag}"

def run(now, state, info):
    day, wd = now.date(), now.weekday()   # دوشنبه=۰ ... پنجشنبه=۳، جمعه=۴
    city = settings()["city"]
    dl = date_line(day, info["hijri"])

    # ۱) اذان: سر وقت (در صورت لزوم تا چند دقیقه صبر می‌کند)
    for name, label in PRAYERS:
        key = f"{day}:{name}"
        hhmm = info["times"][name]
        diff = (at(now, hhmm) - now_tehran()).total_seconds()
        if done(state, key) or diff > SLEEP_MAX or diff < -LATE:
            continue
        photo = fetch_photo(state)   # قبل از صبر کردن آماده می‌شود تا اذان دیر نشود
        diff = (at(now, hhmm) - now_tehran()).total_seconds()
        if diff > 0:
            time.sleep(diff)
        text = (f"🕌 {label} به افق {city}\n🕐 ساعت {fa(hhmm)}\n{dl}\n\n"
                f"قبول طاعات 🤲\n#اذان")
        post(state, key, text, photo)

    # ۲) نوبت‌های ثابت روزانه/هفتگی
    slots = [
        ("06:00", "card", None, None),
        ("07:00", "morning", None, lambda: dhikr_text("🌅 ذکر صبحگاهی", pick(ADHKAR, day), "#ذکر")),
        ("08:00", "occasion", None, None),   # مناسبت؛ پایین‌تر ساخته می‌شود
        ("16:00", "dua", None, lambda: dhikr_text("🤲 دعا", pick(DUAS, day), "#دعا")),
        ("21:30", "night", None, lambda: dhikr_text("🌙 ذکر شبانه", pick(ADHKAR, day, 3), "#ذکر")),
        ("20:00", "kumayl", 3, lambda: "🕯️ امشب شب جمعه است\n\nشبی مناسب برای دعا، زیارت امام حسین (ع) و خواندن دعای کمیل.\n\n#شب_جمعه"),
        ("07:30", "nodbeh", 4, lambda: "🌿 جمعه است\n\nصبح جمعه، وقت دعای ندبه و یاد امام زمان (عج).\nصلوات بر محمد و آل محمد فراموش نشود.\n\n#جمعه"),
    ]
    for hhmm, name, only_wd, build in slots:
        key = f"{day}:{name}"
        diff = (at(now, hhmm) - now_tehran()).total_seconds()
        if done(state, key) or diff > EARLY or diff < -LATE:
            continue
        if only_wd is not None and wd != only_wd:
            continue
        if name == "card":
            post_card(state, key, day, info["hijri"])
            continue
        if name == "occasion":
            title = OCCASIONS.get(info["hijri"][:2])
            if not title:
                mark(state, key)
                continue
            text = f"🌙 مناسبت امروز\n\n{title}\n\n{dl}\n\n#مناسبت"
        else:
            text = build()
        post(state, key, text, fetch_photo(state))

def run_test(now, info):
    """اجرای آزمایشی: فوراً کارت تاریخ و یک پست نمونه با عکس می‌فرستد (بدون ثبت در تاریخچه)."""
    state = {"published": []}
    day = now.date()
    post_card(state, "test:card", day, info["hijri"])
    text = (f"🧪 تست ربات اذان\n🕐 ساعت {fa(now.strftime('%H:%M'))}\n"
            f"{date_line(day, info['hijri'])}\n\nاگر این پست را می‌بینید، ربات درست کار می‌کند ✅")
    post(state, "test:post", text, fetch_photo(state))

def main():
    now = now_tehran()
    state = load_state()
    try:
        info = get_day(now.date())
    except Exception as exc:
        print(f"timings API failed: {exc}")
        raise SystemExit(1)   # خطای قرمز تا مشکل دیده شود
    print(f"now={now:%Y-%m-%d %H:%M} times={info['times']} hijri={info['hijri']}")
    if os.getenv("FORCE_TEST") == "1":
        run_test(now, info)
        return
    before = len(state["published"])
    run(now, state, info)
    if len(state["published"]) == before:
        print("Nothing due right now (this is normal between scheduled times).")
    save_state(state)

if __name__ == "__main__":
    main()
