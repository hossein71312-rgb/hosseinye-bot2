import os
import requests

HIJRI_MONTHS = ["", "محرم", "صفر", "ربیع‌الاول", "ربیع‌الثانی", "جمادی‌الاول", "جمادی‌الثانی",
                "رجب", "شعبان", "رمضان", "شوال", "ذی‌القعده", "ذی‌الحجه"]

def settings():
    return {
     "lat": os.getenv("LAT") or "38.0800",
"lon": os.getenv("LON") or "46.2919",
"city": os.getenv("CITY_NAME") or "تبریز",
        "method": os.getenv("METHOD") or "7",      # ۷ = مؤسسهٔ ژئوفیزیک دانشگاه تهران
        "adjust": os.getenv("HIJRI_ADJUST") or "0",
        "tune": os.getenv("TUNE") or "",   # اختیاری: تنظیم دقیقه‌ای، مثلاً 0,0,0,1,0,1,0,0,0
    }

def get_day(day):
    s = settings()
    url = f"https://api.aladhan.com/v1/timings/{day.strftime('%d-%m-%Y')}"
    params = {"latitude": s["lat"], "longitude": s["lon"], "method": s["method"],
              "timezonestring": "Asia/Tehran", "adjustment": s["adjust"]}
    if s["tune"]:
        params["tune"] = s["tune"]   # ترتیب: Imsak,Fajr,Sunrise,Dhuhr,Asr,Maghrib,Sunset,Isha,Midnight
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()["data"]
    t = data["timings"]
    h = data["date"]["hijri"]
    return {
        "times": {k: t[k][:5] for k in ("Fajr", "Sunrise", "Dhuhr", "Maghrib")},
        "hijri": (int(h["month"]["number"]), int(h["day"]), int(h["year"])),
    }
