import html
import re
import requests

API = "https://commons.wikimedia.org/w/api.php"
UA = {"User-Agent": "PrayerTimesBot/1.0 (Rubika channel publisher)"}
BAD_TITLE = ("map", "flag", "logo", "coat of arms", "diagram", "plan", "poster", "stamp",
             "banknote", "drawing", "painting", "locator", "route", "chart", "satellite", "nasa")
MIN_WIDTH = 1800  # فقط عکس باکیفیت

def clean(value):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value or ""))).strip()

def _license_ok(name):
    return bool(re.match(r"^(cc|public domain|pd)", name.strip().lower()))

def _query(search, offset=0):
    params = {
        "action": "query", "generator": "search", "gsrsearch": f"{search} filetype:bitmap",
        "gsrnamespace": 6, "gsrlimit": 30, "gsroffset": offset,
        "prop": "imageinfo", "iiprop": "url|extmetadata|size|mime",
        "iiurlwidth": 2000, "format": "json",
    }
    r = requests.get(API, params=params, headers=UA, timeout=30)
    r.raise_for_status()
    pages = r.json().get("query", {}).get("pages", {}).values()
    return sorted(pages, key=lambda p: p.get("index", 0))

def _download_best(pages, output_path, skip):
    for page in pages:
        title = page.get("title", "")
        key = f"commons:{title}"
        if skip(key) or any(b in title.lower() for b in BAD_TITLE):
            continue
        info = (page.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata", {})
        lic = clean(meta.get("LicenseShortName", {}).get("value", ""))
        url = info.get("thumburl") or info.get("url")
        w, h = info.get("width", 0), info.get("height", 0)
        if not url or not _license_ok(lic) or info.get("mime") != "image/jpeg":
            continue
        if w < MIN_WIDTH or w < h:   # فقط افقی
            continue
        img = requests.get(url, headers=UA, timeout=60)
        if img.status_code != 200 or not img.headers.get("Content-Type", "").startswith("image/"):
            continue
        if len(img.content) > 9_000_000:
            continue
        with open(output_path, "wb") as f:
            f.write(img.content)
        artist = clean(meta.get("Artist", {}).get("value", ""))[:60]
        return {"license": lic, "artist": artist, "title": title, "key": key}
    return None

def by_place(query, output_path, skip):
    return _download_best(_query(query), output_path, skip)
