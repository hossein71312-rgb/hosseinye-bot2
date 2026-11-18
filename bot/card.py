import os
import tempfile
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

FONT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "Vazirmatn-Bold.ttf")
W = H = 800

def rtl(text):
    return get_display(arabic_reshaper.reshape(text), base_dir="R")

def _font(size):
    return ImageFont.truetype(FONT, size, layout_engine=ImageFont.Layout.BASIC)

def _center(draw, xy_center, text, font, fill):
    cx, cy = xy_center
    draw.text((cx, cy), text, font=font, fill=fill, anchor="mm")

def make_card(wd_fa, wd_en, day, month_fa, gregorian, hijri_line, handle="", friday=False):
    """کارت تاریخ روز (شبیه استیکر تقویم). خروجی: مسیر فایل PNG."""
    main, dark, light, bg = ((0x1E, 0x8E, 0x5A), (0x0E, 0x5A, 0x38), (0xE8, 0xF8, 0xEE), (0xCB, 0xEF, 0xD9)) \
        if friday else ((0xF0, 0x6A, 0x1E), (0xB8, 0x3C, 0x0C), (0xFF, 0xF3, 0xD6), (0xFF, 0xD8, 0x4D))
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)
    # حاشیهٔ بیرونی و پس‌زمینهٔ کارت
    d.rounded_rectangle((40, 40, W - 40, H - 40), radius=90, fill=light, outline=main, width=16)
    # نام روز (فارسی) و انگلیسی
    d.rounded_rectangle((120, 85, W - 120, 205), radius=40, fill="white", outline=main, width=6)
    _center(d, (W // 2, 145), rtl(wd_fa), _font(78), dark)
    d.rounded_rectangle((220, 220, W - 220, 285), radius=32, fill=main)
    _center(d, (W // 2, 253), wd_en, _font(44), "white")
    # روز و ماه شمسی
    d.rounded_rectangle((110, 305, W - 110, 510), radius=50, fill="white", outline=main, width=6)
    _center(d, (W // 2 + 130, 410), str(day), _font(170), dark)
    _center(d, (W // 2 - 190, 410), rtl(month_fa), _font(96), main)
    # میلادی و قمری
    d.rounded_rectangle((110, 530, W - 110, 605), radius=36, fill=main)
    _center(d, (W // 2, 568), gregorian, _font(46), "white")
    d.rounded_rectangle((110, 620, W - 110, 695), radius=36, fill=dark)
    _center(d, (W // 2, 658), rtl(hijri_line), _font(46), "white")
    if handle:
        _center(d, (W // 2, 722), handle, _font(30), dark)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as t:
        path = t.name
    img.save(path)
    return path
