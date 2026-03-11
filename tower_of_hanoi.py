#!/usr/bin/env python3
"""
TOWER OF HANOI — PIXEL EDITION
Full pixel-art gaming aesthetic. No 8-digit hex colors.
"""
import tkinter as tk
import time, json, os, random, math, socket, threading

try:
    from PIL import Image, ImageDraw, ImageFont, ImageTk
    _PIL = True
except ImportError:
    _PIL = False

# ═══════════════════════════════════════════════════════════
#  PALETTE  (6-digit hex only — tkinter safe)
# ═══════════════════════════════════════════════════════════
P = {
    "bg":     "#080810",
    "bg2":    "#0e0e1c",
    "panel":  "#12122a",
    "border": "#1e1e40",
    "grid":   "#14143a",
    "text":   "#dde2ff",
    "muted":  "#4a4a7a",
    "accent": "#00ffcc",
    "pink":   "#ff2d78",
    "yellow": "#ffe600",
    "orange": "#ff7b00",
    "purple": "#bf00ff",
    "blue":   "#0088ff",
    "green":  "#00ff44",
    "red":    "#ff1144",
    "white":  "#ffffff",
    "dark1":  "#1a1a3a",
    "dark2":  "#222244",
}

DISK_PAL = [
    ("#ff1144","#ff6688"),
    ("#ff7b00","#ffaa44"),
    ("#ffe600","#ffee77"),
    ("#00ff44","#66ff88"),
    ("#00ffcc","#66ffee"),
    ("#0088ff","#44aaff"),
    ("#bf00ff","#dd66ff"),
    ("#ff2d78","#ff77aa"),
]

SCORES_FILE = "hanoi_scores.json"
NET_PORT    = 9876

FNT  = lambda s: ("Courier New", s, "normal")
FNTB = lambda s: ("Courier New", s, "bold")


# ═══════════════════════════════════════════════════════════
#  PIXEL RENDERER  (Pillow-based, falls back to canvas if unavailable)
# ═══════════════════════════════════════════════════════════
_img_cache = {}   # str key → PhotoImage (kept alive to prevent GC)

def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def _rgb_to_hex(r, g, b):
    return f"#{r:02x}{g:02x}{b:02x}"

class PixelArt:
    """
    Draw pixel-art bitmaps using Pillow.
    All drawing is done at SCALE×SCALE per logical pixel, then the image
    is placed on a tkinter Canvas as a PhotoImage.

    Usage:
        art = PixelArt(width=16, height=16, scale=4, bg="#080810")
        art.pixel(2, 3, "#00ffcc")          # set 1 logical pixel
        art.rect(0, 0, 15, 15, "#00ffcc")   # filled rect in logical coords
        art.hline(0, 7, 15, "#ffe600")
        art.vline(7, 0, 15, "#ffe600")
        art.blit(canvas, x, y)              # place on tkinter canvas
        photo = art.photo()                 # get PhotoImage directly
    """
    SCALE = 4   # logical pixels → screen pixels

    def __init__(self, width, height, scale=None, bg="#080810"):
        self._W  = width
        self._H  = height
        self._sc = scale or self.SCALE
        if _PIL:
            self._img  = Image.new("RGB",
                                   (width * self._sc, height * self._sc),
                                   _hex_to_rgb(bg))
            self._draw = ImageDraw.Draw(self._img)
        else:
            self._img  = None
            self._draw = None
        self._bg   = bg
        self._ops  = []   # fallback canvas ops

    # ── drawing primitives ─────────────────────────────────────────────────
    def pixel(self, lx, ly, color):
        s = self._sc
        if _PIL and self._draw:
            self._draw.rectangle([lx*s, ly*s, lx*s+s-1, ly*s+s-1],
                                 fill=_hex_to_rgb(color))
        else:
            self._ops.append(("rect", lx*s, ly*s, lx*s+s, ly*s+s, color))

    def rect(self, lx0, ly0, lx1, ly1, color, outline=None):
        s = self._sc
        if _PIL and self._draw:
            self._draw.rectangle([lx0*s, ly0*s, lx1*s+s-1, ly1*s+s-1],
                                 fill=_hex_to_rgb(color),
                                 outline=_hex_to_rgb(outline) if outline else None)
        else:
            self._ops.append(("rect", lx0*s, ly0*s, lx1*s+s, ly1*s+s, color))

    def hline(self, lx0, ly, lx1, color, thick=1):
        self.rect(lx0, ly, lx1, ly+thick-1, color)

    def vline(self, lx, ly0, ly1, color, thick=1):
        self.rect(lx, ly0, lx+thick-1, ly1, color)

    def text_row(self, lx, ly, text, color, char_map=None):
        """Draw text using a tiny 3×5 pixel font."""
        _FONT3 = {
            "A":["010","101","111","101","101"],
            "B":["110","101","110","101","110"],
            "C":["011","100","100","100","011"],
            "D":["110","101","101","101","110"],
            "E":["111","100","110","100","111"],
            "F":["111","100","110","100","100"],
            "G":["011","100","101","101","011"],
            "H":["101","101","111","101","101"],
            "I":["111","010","010","010","111"],
            "J":["001","001","001","101","010"],
            "K":["101","110","100","110","101"],
            "L":["100","100","100","100","111"],
            "M":["101","111","111","101","101"],
            "N":["101","111","111","101","101"],
            "O":["010","101","101","101","010"],
            "P":["110","101","110","100","100"],
            "Q":["010","101","101","110","011"],
            "R":["110","101","110","101","101"],
            "S":["011","100","010","001","110"],
            "T":["111","010","010","010","010"],
            "U":["101","101","101","101","011"],
            "V":["101","101","101","010","010"],
            "W":["101","101","111","111","101"],
            "X":["101","101","010","101","101"],
            "Y":["101","101","010","010","010"],
            "Z":["111","001","010","100","111"],
            "0":["010","101","101","101","010"],
            "1":["010","110","010","010","111"],
            "2":["110","001","010","100","111"],
            "3":["110","001","010","001","110"],
            "4":["101","101","111","001","001"],
            "5":["111","100","110","001","110"],
            "6":["011","100","110","101","010"],
            "7":["111","001","010","010","010"],
            "8":["010","101","010","101","010"],
            "9":["010","101","011","001","110"],
            " ":["000","000","000","000","000"],
            ":":["000","010","000","010","000"],
            "/":["001","001","010","100","100"],
            "!":["010","010","010","000","010"],
            "-":["000","000","111","000","000"],
            ">":["100","010","001","010","100"],
            "<":["001","010","100","010","001"],
            "+":["000","010","111","010","000"],
            "*":["101","010","111","010","101"],
            ".":["000","000","000","000","010"],
            "[":["110","100","100","100","110"],
            "]":["011","001","001","001","011"],
            "|":["010","010","010","010","010"],
        }
        cx = lx
        for ch in text.upper():
            glyph = _FONT3.get(ch, _FONT3.get(" "))
            for gy, row in enumerate(glyph):
                for gx, bit in enumerate(row):
                    if bit == "1":
                        self.pixel(cx+gx, ly+gy, color)
            cx += 4   # 3 wide + 1 gap

    def fill(self, color):
        if _PIL and self._img:
            self._img.paste(_hex_to_rgb(color),
                            [0, 0, self._W*self._sc, self._H*self._sc])

    def photo(self, key=None):
        """Return a tk.PhotoImage. Pass key to cache and prevent GC."""
        if _PIL and self._img:
            photo = ImageTk.PhotoImage(self._img)
        else:
            # Fallback: create a plain colored PhotoImage
            photo = tk.PhotoImage(width=self._W*self._sc,
                                  height=self._H*self._sc)
        if key:
            _img_cache[key] = photo   # prevent garbage collection
        return photo

    def blit(self, canvas, cx, cy, anchor="nw", key=None):
        """Place this image on a tkinter canvas at (cx,cy)."""
        photo = self.photo(key=key)
        canvas.create_image(cx, cy, image=photo, anchor=anchor)
        return photo

    @property
    def width(self):  return self._W * self._sc

    @property
    def height(self): return self._H * self._sc


# ── Icon renderer using PixelArt ─────────────────────────────────────────────
def make_icon(icon_id, size_px=32, color="#00ffcc", bg="#080810", scale=None):
    """
    Render a pixel-art icon as a PixelArt object using Pillow.

    All built-in icons are hand-designed on a logical grid.  By default the
    grid is 16×16, but certain ``_detailed`` variants use a 32×32 grid for
    extra pixels.  Additionally if ``icon_id`` starts with ``"url:"`` the
    remainder is treated as an HTTP URL; the image will be downloaded and
    snapped to a nearest‑neighbor bitmap sized to the requested ``size_px``.

    Examples:
        # use the high‑resolution version of the play button
        art = make_icon("play_detailed", size_px=64)

        # fetch a small pixel icon from the web and cache it
        art = make_icon("url:https://example.com/icon16.png", size_px=32)
    """
    import math as _m

    # handle URL-based icons first
    if icon_id.startswith("url:"):
        if not _PIL:
            # fallback: simple placeholder
            GW = 16
            sc = scale or max(1, size_px // GW)
            art = PixelArt(GW, GW, scale=sc, bg=bg)
            art.fill(color)
            return art
        from io import BytesIO
        import urllib.request
        url = icon_id[4:]
        try:
            with urllib.request.urlopen(url, timeout=3) as resp:
                data = resp.read()
            im = Image.open(BytesIO(data)).convert("RGB")
            # resize to requested pixel size
            im = im.resize((size_px, size_px), resample=Image.NEAREST)
            art = PixelArt(size_px, size_px, scale=1, bg=bg)
            art._img = im
            art._draw = ImageDraw.Draw(im)
            return art
        except Exception:
            # on failure use a plain color square
            GW = 16
            sc = scale or max(1, size_px // GW)
            art = PixelArt(GW, GW, scale=sc, bg=bg)
            art.fill(color)
            return art

    # detailed versions use a double-resolution grid
    detailed = icon_id.endswith("_detailed")
    if detailed:
        icon_id = icon_id[: -len("_detailed")]
        GW = 32
    else:
        GW = 16

    sc = scale or max(1, size_px // GW)
    art = PixelArt(GW, GW, scale=sc, bg=bg)
    c    = color
    bg_  = bg
    Y    = P.get("yellow","#ffe600")
    W    = P.get("white","#ffffff")

    # helper functions need to respect logical grid scaling
    sf = GW // 16  # scale factor (1 for regular icons, 2 for detailed)
    def p(lx, ly, col=None):
        """plot one logical pixel, expanded by sf×sf when detailed."""
        col = col or c
        if sf == 1:
            art.pixel(lx, ly, col)
        else:
            # draw a block of sf×sf pixels
            for dx in range(sf):
                for dy in range(sf):
                    art.pixel(lx*sf + dx, ly*sf + dy, col)
    def row(ly, xs, col=None):
        for lx in xs: p(lx, ly, col)
    def col_px(lx, ys, col=None):
        for ly in ys: p(lx, ly, col)
    def rect(x0, y0, x1, y1, col=None):
        col = col or c
        for y in range(y0, y1+1):
            for x in range(x0, x1+1): p(x, y, col)

    if icon_id == "back":       # solid left arrow
        for r, w in enumerate([1,2,3,4,5,6,7,8,7,6,5,4,3,2,1]):
            for i in range(w): p(7-w+1+i, r)

    elif icon_id == "play":     # solid right arrow
        for r, w in enumerate([1,2,3,4,5,6,7,8,7,6,5,4,3,2,1]):
            for i in range(w): p(3+i, r)
        if detailed:
            # add a contrast outline and a drop shadow for large icons
            # outline: draw border one pixel around the shape
            for r, w in enumerate([1,2,3,4,5,6,7,8,7,6,5,4,3,2,1]):
                xstart = 3
                xend = 3 + w - 1
                # top/bottom border
                p(xstart-1, r, "#000000")
                p(xend+1, r, "#000000")
            for r in range(14):
                p(3 + (r*1)//2, r+1, "#000000")
            # drop shadow at bottom-right
            for r, w in enumerate([1,2,3,4,5,6,7,8,7,6,5,4,3,2,1]):
                for i in range(w): p(3+i+1, r+1, "#222222")

    elif icon_id == "bolt":     # lightning bolt Z
        rect(7,1,13,3)
        for i in range(4): p(7-i,3+i); p(8-i,3+i); p(8-i,4+i)
        rect(3,7,9,9)
        for i in range(4): p(9-i,9+i); p(10-i,9+i); p(9-i,10+i)
        rect(2,12,8,14)
        if detailed:
            # thicker stroke + highlight
            for i in range(0, 16, 2):
                p(7-i//2,1+i//4, "#ffffff")
            # faint glow
            for dx in (-1,1):
                for dy in (-1,1):
                    rect(7+dx,1+dy,13+dx,3+dy, "#444444")

    elif icon_id == "star":     # 5-point star (scanline fill)
        cx2,cy2 = 8.0,8.0
        pts = []
        for i in range(5):
            a = _m.radians(-90+i*72); ai = _m.radians(-90+i*72+36)
            pts.append((cx2+6.5*_m.cos(a), cy2+6.5*_m.sin(a)))
            pts.append((cx2+2.8*_m.cos(ai),cy2+2.8*_m.sin(ai)))
        for sy in range(GW):
            xs = []
            n = len(pts)
            for i in range(n):
                x1,y1=pts[i]; x2,y2=pts[(i+1)%n]
                if min(y1,y2)<=sy+0.5<=max(y1,y2):
                    xi=x1+(sy+0.5-y1)*(x2-x1)/((y2-y1)or 1)
                    xs.append(xi)
            xs.sort()
            for i in range(0,len(xs)-1,2):
                for lx in range(int(xs[i]),int(xs[i+1])+1):
                    if 0<=lx<GW: p(lx,sy)

    elif icon_id == "freeze":   # snowflake
        rect(7,1,8,14); rect(1,7,14,8)
        for i in range(4):
            p(4-i,4-i);p(5-i,5-i); p(11+i,4-i);p(10+i,5-i)
            p(4-i,11+i);p(5-i,10+i); p(11+i,11+i);p(10+i,10+i)
        row(1,[5,6,9,10]); row(14,[5,6,9,10])
        col_px(1,[5,6,9,10]); col_px(14,[5,6,9,10])

    elif icon_id == "slowmo":   # hourglass with sand
        rect(2,1,13,2); rect(2,13,13,14)
        for i in range(5): rect(2+i,3+i,13-i,3+i)
        row(8,[7,8])
        for i in range(5): rect(6-i,9+i,9+i,9+i)
        p(6,4,Y); p(9,4,Y); p(7,9,Y); p(8,9,Y)

    elif icon_id == "unlock":   # open padlock
        rect(3,7,12,13); rect(4,8,11,12,bg_)
        rect(6,9,9,11); p(7,10,bg_); p(8,10,bg_)
        p(7,11); p(8,11)
        col_px(3,[3,4,5,6,7]); col_px(4,[2,3])
        row(2,[4,5,6,7,8,9])
        col_px(12,[2,3,4,5,6,7]); row(1,[10,11,12,13])

    elif icon_id == "lock":     # closed padlock
        rect(3,7,12,13); rect(4,8,11,12,bg_)
        rect(6,9,9,11); p(7,10,bg_); p(8,10,bg_)
        p(7,11); p(8,11)
        col_px(3,[3,4,5,6,7]); col_px(12,[3,4,5,6,7])
        row(2,[3,4,5,6,7,8,9,10,11,12]); row(3,[3,4,11,12])
        if detailed:
            # draw keyhole highlight and extra metal texture
            p(7,8, "#dddddd"); p(8,8, "#dddddd")
            for dy in range(7,14,2):
                p(3,dy, "#333333"); p(12,dy, "#333333")

    elif icon_id == "timewarp": # clock face
        rect(3,1,12,2); rect(3,13,12,14)
        rect(1,3,2,12); rect(13,3,14,12)
        rect(2,2,3,3); rect(12,2,13,3)
        rect(2,12,3,13); rect(12,12,13,13)
        rect(3,3,12,12,bg_)
        row(3,[7,8]); row(12,[7,8])
        col_px(3,[7,8]); col_px(12,[7,8])
        col_px(7,[4,5,6,7]); col_px(8,[4,5,6,7])  # hour up
        row(7,[8,9,10,11]); row(8,[8,9,10,11])      # minute right
        rect(7,7,8,8)
        for i in range(3): p(10+i,10+i,Y); p(10+i,12-i,Y)

    elif icon_id == "clear":    # eraser
        for i in range(5): rect(2+i,1+i,7+i,4+i)
        rect(1,9,14,13); rect(1,11,14,11,bg_)
        for lx in [2,5,8,11,13]: p(lx,8)

    elif icon_id == "chaos_bot": # skull
        rect(4,1,11,4); rect(3,2,12,7); rect(2,3,13,6)
        rect(3,7,12,10)
        rect(4,3,6,6,bg_); rect(9,3,11,6,bg_)
        p(7,6,bg_); p(8,6,bg_)
        for x in [4,6,8,10]: p(x,8,bg_); p(x,9,bg_)
        for i in range(5): p(2+i,11+i//2); p(13-i,11+i//2)
        rect(1,11,3,13); rect(12,11,14,13)

    elif icon_id == "trophy":   # cup + star
        rect(4,2,11,8); rect(5,3,10,7,bg_)
        rect(2,3,3,6); rect(12,3,13,6)
        rect(7,9,8,10); rect(4,11,11,12)
        p(7,0,Y); p(8,0,Y)
        for dx in [-1,1]: p(7+dx,1,Y)

    elif icon_id == "sword":    # diagonal sword
        for i in range(9): p(2+i,2+i); p(3+i,2+i)
        rect(3,9,11,10)
        rect(7,11,8,14); rect(6,13,9,14)
        p(2,2,W); p(3,2,W)

    elif icon_id == "block":    # X
        for i in range(12):
            p(2+i,2+i); p(3+i,2+i)
            p(2+i,13-i); p(3+i,13-i)

    elif icon_id == "check":    # checkmark
        for i in range(4): p(2+i,8+i); p(2+i,9+i)
        for i in range(8): p(5+i,11-i); p(5+i,12-i)

    elif icon_id == "robot":    # robot face
        col_px(7,[1,2,3]); col_px(8,[1,2,3])
        rect(6,3,9,4)
        rect(2,4,13,12)
        rect(3,5,12,11,bg_)
        rect(4,6,6,9); rect(9,6,11,9)
        rect(5,7,6,8,W); rect(9,7,10,8,W)
        row(10,[4,5,6,7,8,9,10,11])
        for x in [5,7,9,11]: p(x,10,bg_); p(x,11,bg_)
        rect(1,6,2,9); rect(13,6,14,9)

    elif icon_id == "crown":    # crown
        col_px(2,[5,6,7,8,9,10,11]); col_px(3,[5,6,7,8,9,10,11])
        col_px(7,[2,3,4,5,6,7,8,9,10,11]); col_px(8,[2,3,4,5,6,7,8,9,10,11])
        col_px(12,[5,6,7,8,9,10,11]); col_px(13,[5,6,7,8,9,10,11])
        rect(2,9,13,13)
        rect(7,11,8,12,Y)
        rect(2,12,4,13,Y); rect(11,12,13,13,Y)

    elif icon_id == "menu":     # hamburger
        rect(2,3,13,5); rect(2,7,13,9); rect(2,11,13,13)

    elif icon_id == "restart":  # circular arrow
        rect(3,1,11,3); rect(1,3,3,12)
        rect(3,12,12,14); rect(12,7,14,12)
        rect(5,4,11,11,bg_)
        rect(11,1,14,4)
        p(14,5); p(14,6); p(13,5)

    elif icon_id == "solo":     # person
        rect(5,1,10,5); rect(6,5,9,6)
        rect(3,7,12,10)
        rect(1,7,3,10); rect(12,7,14,10)
        rect(4,11,6,14); rect(9,11,11,14)

    elif icon_id == "multi":    # two people
        rect(1,2,5,5); rect(0,6,6,9)
        rect(1,10,3,13); rect(4,10,6,13)
        rect(8,1,13,5); p(9,2,bg_);p(10,2,bg_);p(11,2,bg_)
        rect(7,6,14,10)
        rect(7,11,9,14); rect(11,11,14,14)

    elif icon_id == "scores":   # podium
        rect(1,6,5,13); rect(6,2,10,13); rect(11,9,14,13)
        rect(0,13,15,15)
        rect(7,0,9,1,Y); p(8,0,Y)
        p(2,4,W);p(3,4,W); p(12,7,W);p(12,8,W)

    elif icon_id == "double":   # two bolts
        rect(1,2,5,3)
        p(4,4);p(3,5);p(2,6)
        rect(1,7,5,8)
        p(4,9);p(3,10);p(2,11)
        rect(1,11,4,12)
        rect(8,1,14,3)
        for i in range(4): p(7-i,3+i);p(8-i,3+i);p(8-i,4+i)
        rect(5,6,11,8)
        for i in range(4): p(9-i,9+i);p(10-i,9+i);p(9-i,10+i)
        rect(8,12,14,14)

    else:   # fallback: question mark
        row(5,[6,7,8,9]); p(10,6); p(10,7); p(9,8)
        p(8,9); p(8,11)

    return art


def icon_photo(icon_id, size_px=32, color="#00ffcc", bg="#080810", scale=None):
    """Get a cached PhotoImage for an icon.

    Keys now include the raw ``icon_id`` so that ``_detailed`` variants or
    ``url:...`` requests are cached separately.  Because URLs may change,
    the cache key equals the full identifier string.
    """
    key = f"{icon_id}_{size_px}_{color}_{bg}"
    if key not in _img_cache:
        art = make_icon(icon_id, size_px=size_px, color=color, bg=bg, scale=scale)
        _img_cache[key] = art.photo(key=key)
    return _img_cache[key]


def make_button_img(text, color, w_px, h_px, scale=2,
                    hovered=False, clicked=False,
                    icon_id=None, bg="#080810", font_size=11):
    """
    Render a complete pixel-art button as a PixelArt image.
    Returns a PixelArt object.
    """
    sc  = scale
    lw  = w_px // sc
    lh  = h_px // sc
    art = PixelArt(lw, lh, scale=sc, bg=bg)
    B   = 3   # border thickness in logical pixels
    off = B if clicked else 0

    col_rgb   = _hex_to_rgb(color)
    body_col  = P["dark2"] if hovered else P["panel"]
    shadow_col= P["bg2"]

    # drop shadow
    if not clicked:
        art.rect(B//2, B//2, lw-1, lh-1, shadow_col)

    # outer border
    art.rect(off, off, lw-B+off, lh-B+off, color)

    # inner body
    art.rect(off+B, off+B, lw-B*2+off, lh-B*2+off, body_col)

    # dither top+left when hovered
    if hovered and not clicked:
        for xx in range(off+B, lw-B+off, 4):
            art.pixel(xx, off+B, color)
            art.pixel(xx+1, off+B, color)
        for yy in range(off+B, lh-B+off, 4):
            art.pixel(off+B, yy, color)
            art.pixel(off+B, yy+1, color)

    # bottom/right inner shadow
    art.hline(off+B, lh-B*2+off, lw-B*2+off, P["bg"])
    art.vline(lw-B*2+off, off+B, lh-B*2+off, P["bg"])

    return art



# ═══════════════════════════════════════════════════════════
#  PIXEL ICON RENDERER  (all icons drawn on Canvas — no emoji)
# ═══════════════════════════════════════════════════════════
def draw_icon(canvas, icon_id, cx, cy, size=20, color="#00ffcc"):
    """
    Draw a pixel-art icon centered at (cx,cy) on a tkinter Canvas.
    If Pillow is available: renders a true pixel bitmap via PixelArt/make_icon.
    Otherwise: falls back to canvas rectangle primitives.
    """
    if _PIL:
        try:
            bg_raw = canvas.cget("background")
            bg = bg_raw if bg_raw.startswith("#") else P["bg"]
        except Exception:
            bg = P["bg"]
        art = make_icon(icon_id, size_px=size, color=color, bg=bg)
        photo = art.photo()
        # store reference on canvas widget to prevent GC
        if not hasattr(canvas, "_icon_refs"):
            canvas._icon_refs = []
        canvas._icon_refs.append(photo)
        canvas.create_image(cx, cy, image=photo, anchor="center")
        return

    # ── Fallback: canvas rectangle blocks ──────────────────────────────────
    g  = max(2, size // 8)
    def p(x, y, col=color):
        canvas.create_rectangle(x, y, x+g, y+g, fill=col, outline="")
    def rct(x0,y0,x1,y1,col=color):
        canvas.create_rectangle(x0,y0,x1,y1,fill=col,outline="")

    if icon_id == "freeze":
        for d in range(-3,4): p(cx+d*g,cy); p(cx,cy+d*g)
        for dx,dy in [(-2,-2),(2,-2),(-2,2),(2,2)]: p(cx+dx*g,cy+dy*g)
        rct(cx-g,cy-g,cx+g,cy+g)
    elif icon_id == "bolt":
        pts=[cx-g,cy-size//2, cx+g,cy-g, cx+g//2*3,cy-g,
             cx+g,cy+size//2, cx-g,cy+g, cx-g//2*3,cy+g]
        canvas.create_polygon(pts,fill=color,outline="")
    elif icon_id == "play":
        h=size//2
        canvas.create_polygon(cx-h//2,cy-h,cx+h,cy,cx-h//2,cy+h,fill=color,outline="")
    elif icon_id == "back":
        h=size//2
        canvas.create_polygon(cx+h//2,cy-h,cx-h,cy,cx+h//2,cy+h,fill=color,outline="")
        rct(cx-h,cy-g//2,cx+h//2,cy+g//2)
    elif icon_id == "restart":
        canvas.create_arc(cx-size//2,cy-size//2,cx+size//2,cy+size//2,
                          start=30,extent=290,outline=color,width=3,style="arc")
    elif icon_id == "robot":
        rct(cx-size//3,cy-size//4,cx+size//3,cy+size//3)
        rct(cx-size//6,cy-size//2,cx+size//6,cy-size//4)
    elif icon_id == "crown":
        pts=[cx-size//2,cy+size//3, cx-size//2,cy-size//6,
             cx-size//4,cy-size//2, cx,cy-size//3,
             cx+size//4,cy-size//2, cx+size//2,cy-size//6,
             cx+size//2,cy+size//3]
        canvas.create_polygon(pts,fill=color,outline="")
    elif icon_id == "scores":
        rct(cx-size//2,cy+size//4,cx-size//4,cy+size//2)
        rct(cx-size//8,cy-size//4,cx+size//8,cy+size//2)
        rct(cx+size//4,cy,cx+size//2,cy+size//2)
    elif icon_id == "menu":
        for dy in (-g,0,g): rct(cx-size//2,cy+dy-g//2,cx+size//2,cy+dy+g//2)
    elif icon_id == "multi":
        canvas.create_oval(cx-size//3,cy-size//2,cx-g,cy-size//4,fill=color,outline="")
        rct(cx-size//3,cy-size//4,cx,cy+size//2)
        canvas.create_oval(cx+g,cy-size//2,cx+size//3,cy-size//4,fill=color,outline="")
        rct(cx,cy-size//4,cx+size//3,cy+size//2)
    elif icon_id == "solo":
        canvas.create_oval(cx-size//4,cy-size//2,cx+size//4,cy-size//6,fill=color,outline="")
        rct(cx-size//3,cy-size//6,cx+size//3,cy+size//2)
    else:
        # generic: draw a filled square
        rct(cx-size//3,cy-size//3,cx+size//3,cy+size//3)


class PixelIcon(tk.Canvas):
    """A small canvas that renders a pixel-art icon."""
    def __init__(self, parent, icon_id, size=22, color="#00ffcc", bg=None):
        bg = bg or P["bg"]
        super().__init__(parent, width=size, height=size,
                         bg=bg, highlightthickness=0)
        self._icon  = icon_id
        self._size  = size
        self._color = color
        self._bg    = bg
        self.bind("<Configure>", lambda e: self._draw())
        self.after(10, self._draw)

    def _draw(self):
        self.delete("all")
        s = self._size
        draw_icon(self, self._icon, s//2, s//2, size=s-4, color=self._color)

    def set_color(self, col):
        self._color = col
        self._draw()



# ═══════════════════════════════════════════════════════════
#  SCORES
# ═══════════════════════════════════════════════════════════
class Scores:
    def __init__(self):
        self.data = {"classic":[], "chaos":[]}
        try:
            if os.path.exists(SCORES_FILE):
                self.data = json.load(open(SCORES_FILE))
        except Exception:
            pass

    def save(self):
        try:
            json.dump(self.data, open(SCORES_FILE,"w"), indent=2)
        except Exception:
            pass

    def add(self, mode, name, disks, moves, secs):
        opt   = (2**disks)-1
        score = max(0, int((opt/max(moves,1))*1000*disks - secs*1.5 + disks*60))
        e = {"name":name,"disks":disks,"moves":moves,
             "time":round(secs,1),"score":score}
        k = mode if mode in self.data else "classic"
        self.data[k].append(e)
        self.data[k].sort(key=lambda x: -x["score"])
        self.data[k] = self.data[k][:15]
        self.save()
        return score

    def top(self, mode, n=12):
        return self.data.get(mode, [])[:n]


# ═══════════════════════════════════════════════════════════
#  PARTICLES
# ═══════════════════════════════════════════════════════════
class Spark:
    __slots__ = ("x","y","vx","vy","life","ml","color","sz")
    def __init__(self, x, y, color, speed):
        self.x, self.y = float(x), float(y)
        a = random.uniform(0, math.tau)
        s = random.uniform(1.0, speed)
        self.vx = math.cos(a)*s
        self.vy = math.sin(a)*s
        self.ml = self.life = random.randint(20, 45)
        self.color = color
        self.sz    = random.randint(2, 5)

class Particles:
    def __init__(self):
        self.sparks = []

    def burst(self, x, y, color, n=28, speed=5.0):
        for _ in range(n):
            self.sparks.append(Spark(x, y, color, speed))

    def explosion(self, x, y, colors, n=80):
        for col in colors:
            self.burst(x, y, col, n=n//len(colors), speed=7.0)

    def update(self):
        alive = []
        for s in self.sparks:
            s.x  += s.vx
            s.y  += s.vy
            s.vy += 0.22
            s.vx *= 0.94
            s.life -= 1
            if s.life > 0:
                alive.append(s)
        self.sparks = alive

    def draw(self, canvas):
        for s in self.sparks:
            r = max(1, int(s.sz * s.life / s.ml))
            canvas.create_rectangle(
                s.x-r, s.y-r, s.x+r, s.y+r,
                fill=s.color, outline=""
            )


# ═══════════════════════════════════════════════════════════
#  SHAKER
# ═══════════════════════════════════════════════════════════
class Shaker:
    def __init__(self):
        self.t = 0
        self.mag = 0

    def trigger(self, mag=6):
        self.t = 10
        self.mag = mag

    def offset(self):
        if self.t <= 0:
            return 0, 0
        self.t -= 1
        m = self.mag * self.t / 10
        return (random.randint(-int(m), int(m)),
                random.randint(-int(m)//2, int(m)//2))


# ═══════════════════════════════════════════════════════════
#  HANOI STATE
# ═══════════════════════════════════════════════════════════
class HanoiState:
    def __init__(self, n):
        self.n       = n
        self.pegs    = [list(range(n, 0, -1)), [], []]
        self.moves   = 0
        self.locked  = set()
        self.blocked = set()

    def top(self, p):
        return self.pegs[p][-1] if self.pegs[p] else None

    def can_move(self, src, dst):
        if not self.pegs[src]:
            return False, "EMPTY PEG"
        if self.top(src) in self.locked:
            return False, "DISK LOCKED!"
        if dst in self.blocked:
            return False, "PEG BLOCKED!"
        if self.pegs[dst] and self.top(dst) < self.top(src):
            return False, "ILLEGAL MOVE!"
        return True, ""

    def do_move(self, src, dst):
        ok, msg = self.can_move(src, dst)
        if ok:
            self.pegs[dst].append(self.pegs[src].pop())
            self.moves += 1
        return ok, msg

    @property
    def solved(self):
        return len(self.pegs[2]) == self.n

    def optimal(self):
        return (2**self.n) - 1


# ═══════════════════════════════════════════════════════════
#  BOARD CANVAS
# ═══════════════════════════════════════════════════════════
class BoardCanvas(tk.Canvas):
    TICK = 33

    def __init__(self, master, state, interactive=True, label=""):
        super().__init__(master,
                         bg=P["bg"],
                         highlightthickness=3,
                         highlightbackground=P["accent"],
                         width=460, height=400)
        self.state       = state
        self.interactive = interactive
        self.label       = label
        self.selected    = None
        self.parts       = Particles()
        self.shaker      = Shaker()
        self.on_move     = None
        self.on_select   = None   # callback(peg) when player lifts a disk

        self._flash_col = None
        self._flash_t   = 0
        self._stars     = None

        # flying disk animation state
        self._fly_disk  = None
        self._fly_x     = 0.0
        self._fly_y     = 0.0
        self._fly_tx    = 0.0
        self._fly_ty    = 0.0
        self._fly_steps = 0
        self._fly_total = 14

        # opponent ghost: shows which peg the other player has picked up from
        # set externally: (peg_idx, disk_id) or None
        self.op_selected = None      # peg index the opponent picked up from
        self._ghost_t    = 0.0       # animation phase (0..2pi, cycles)

        self.bind("<Button-1>",  self._click)
        self.bind("<Configure>", lambda e: self._reset_stars())
        self._loop()

    def _reset_stars(self):
        self._stars = None

    def _make_stars(self, W, H):
        self._stars = [
            (random.randint(2, W-2),
             random.randint(2, H-2),
             random.choice([P["accent"], P["yellow"], P["white"], P["muted"]]),
             random.randint(1, 3))
            for _ in range(55)
        ]

    def _loop(self):
        self.parts.update()
        if self._flash_t > 0:
            self._flash_t -= 1
        if self._fly_disk is not None:
            self._step_fly()
        if self.op_selected is not None:
            self._ghost_t = (self._ghost_t + 0.18) % (2 * math.pi)
        self._render()
        self.after(self.TICK, self._loop)

    # ── render ────────────────────────────────────────────
    def _render(self):
        self.delete("all")
        W = max(self.winfo_width(),  460)
        H = max(self.winfo_height(), 400)
        sx, sy = self.shaker.offset()

        # starfield
        if self._stars is None:
            self._make_stars(W, H)
        for bx, by, bc, bsz in self._stars:
            self.create_rectangle(bx, by, bx+bsz, by+bsz, fill=bc, outline="")

        # pixel grid
        for gx in range(0, W, 20):
            self.create_line(gx, 0, gx, H, fill=P["grid"])
        for gy in range(0, H, 20):
            self.create_line(0, gy, W, gy, fill=P["grid"])

        # scanlines (stipple — no alpha needed)
        for yy in range(0, H, 4):
            self.create_line(0, yy, W, yy, fill=P["bg"], stipple="gray25")

        # board label
        if self.label:
            self.create_text(W//2+sx, 18+sy,
                             text=self.label,
                             fill=P["yellow"], font=FNTB(10), anchor="center")

        # geometry
        PAD    = 32
        base_y = H - 68 + sy
        peg_H  = int((H - 100) * 0.78)
        col_W  = (W - PAD*2) / 3
        peg_xs = [int(PAD + col_W*(k+0.5)) + sx for k in range(3)]
        n      = self.state.n
        dh     = max(14, min(30, (peg_H - 16) // (n + 2)))
        max_dw = int(col_W * 0.86)

        # ground platform — chunky 3-row pixel bar
        shades = ["#1a1a44", "#22224e", "#2a2a5a"]
        for row, shade in enumerate(shades):
            self.create_rectangle(
                PAD-12+sx, base_y + row*5,
                W-PAD+12+sx, base_y + row*5 + 6,
                fill=shade, outline=""
            )
        self.create_line(PAD-12+sx, base_y, W-PAD+12+sx, base_y,
                         fill=P["accent"], width=2)

        # pegs
        pegs = self.state.pegs
        for k, px in enumerate(peg_xs):
            blocked = k in self.state.blocked
            is_sel  = (k == self.selected)

            # selection glow
            if is_sel:
                for gi in range(4, 0, -1):
                    self.create_rectangle(
                        px - max_dw//2 - gi*3, base_y - peg_H - gi*3,
                        px + max_dw//2 + gi*3, base_y + gi*3,
                        outline=P["accent"], fill="", width=1
                    )

            # rod
            rod_col = P["red"]   if blocked else P["dark2"]
            rod_hi  = P["red"]   if blocked else P["muted"]
            self.create_rectangle(px-6, base_y-peg_H, px+6, base_y,
                                  fill=rod_col, outline="")
            self.create_rectangle(px-6, base_y-peg_H, px-3, base_y,
                                  fill=rod_hi, outline="")

            # cap
            cap_col = P["red"] if blocked else P["accent"]
            self.create_rectangle(px-8, base_y-peg_H-6, px+8, base_y-peg_H,
                                  fill=cap_col, outline="")

            # label
            lbl_col = P["accent"] if is_sel else P["muted"]
            self.create_text(px, base_y+28, text=["A","B","C"][k],
                             fill=lbl_col, font=FNTB(13), anchor="center")

            if blocked:
                self.create_text(px, base_y-peg_H-20, text="BLOCKED",
                                 fill=P["red"], font=FNTB(8), anchor="center")

            # disks
            for j, disk in enumerate(pegs[k]):
                # skip if being animated away
                if (self._fly_disk == disk and
                        self._fly_steps > 0):
                    continue
                dy = base_y - (j+1)*(dh+2)
                self._draw_disk(disk, px, dy, dh, max_dw, n)

        # flying disk
        if self._fly_disk is not None:
            self._draw_disk(self._fly_disk,
                            int(self._fly_x), int(self._fly_y),
                            dh, max_dw, n, flying=True)

        # lifted disk bobbing above selected peg
        if self.selected is not None and pegs[self.selected]:
            td     = pegs[self.selected][-1]
            px     = peg_xs[self.selected]
            lift_y = base_y - len(pegs[self.selected])*(dh+2) - 44
            bob    = int(math.sin(time.time()*4) * 4)
            self._draw_disk(td, px, lift_y+bob, dh, max_dw, n, flying=True)

        # particles
        self.parts.draw(self)

        # error flash (stipple, no alpha)
        if self._flash_t > 0:
            stip = "gray50" if self._flash_t > 5 else "gray25"
            self.create_rectangle(0, 0, W, H,
                                  fill=self._flash_col,
                                  outline="", stipple=stip)

        # ── opponent ghost selection indicator ──────────────
        if self.op_selected is not None:
            pg = self.op_selected
            if 0 <= pg < 3 and self.state.pegs[pg]:
                disk  = self.state.pegs[pg][-1]
                base_col, hi_col = DISK_PAL[(disk-1) % len(DISK_PAL)]
                max_dw = (col_W * 0.88)
                dw     = max(26, int(max_dw * disk / self.state.n))
                dh_    = max(14, min(30, (int((H-100)*0.78)-16)//(self.state.n+2)))
                # bob up and down
                bob    = int(math.sin(self._ghost_t) * 7)
                gx     = peg_xs[pg] + sx
                gy     = base_y - len(self.state.pegs[pg]) * (dh_+2) - 18 + bob + sy
                # ghost disk (semi-transparent using stipple)
                self.create_rectangle(gx-dw//2-2, gy-2,
                                      gx+dw//2+2, gy+dh_+2,
                                      fill=base_col, outline="", stipple="gray50")
                self.create_rectangle(gx-dw//2, gy,
                                      gx+dw//2, gy+dh_,
                                      fill=hi_col, outline="", stipple="gray50")
                # solid outline so it's visible
                self.create_rectangle(gx-dw//2-2, gy-2,
                                      gx+dw//2+2, gy+dh_+2,
                                      outline=hi_col, fill="", width=2)
                # "THINKING" pulse label above disk
                alpha = int(abs(math.sin(self._ghost_t)) * 255)
                pulse_col = hi_col if int(self._ghost_t / math.pi) % 2 == 0 else P["white"]
                self.create_text(gx, gy - 14,
                                 text="< THINKING >",
                                 fill=pulse_col, font=FNTB(7), anchor="center")
                # peg highlight column
                self.create_rectangle(peg_xs[pg]+sx-3, 30+sy,
                                      peg_xs[pg]+sx+3, base_y+sy,
                                      fill=hi_col, outline="", stipple="gray25")

        # ── keyboard key hints below peg labels
        if self.interactive:
            keys = ["A", "S", "D"]
            for k, px in enumerate(peg_xs):
                key  = keys[k]
                kx   = px
                ky   = base_y + 48
                sel  = (k == self.selected)
                kfg  = P["accent"] if sel else P["muted"]
                kbg  = P["dark2"]  if sel else P["panel"]
                # pixel key cap
                self.create_rectangle(kx-13, ky-10, kx+13, ky+10,
                                      fill=kbg, outline=kfg, width=1)
                # top highlight stripe
                self.create_rectangle(kx-13, ky-10, kx+13, ky-8,
                                      fill=kfg, outline="")
                self.create_text(kx, ky+1, text=key, fill=kfg,
                                 font=FNTB(9), anchor="center")

        # solved overlay
        if self.state.solved:
            self._draw_solved(W, H, sx, sy)

    def _draw_disk(self, disk, cx, dy, dh, max_dw, n, flying=False):
        dw   = max(26, int(max_dw * disk / n))
        base, hi = DISK_PAL[(disk-1) % len(DISK_PAL)]
        locked = disk in self.state.locked

        # pixel shadow
        self.create_rectangle(cx-dw//2+4, dy+5,
                               cx+dw//2+4, dy+dh+5,
                               fill="#000000", outline="")
        # body
        self.create_rectangle(cx-dw//2, dy,
                               cx+dw//2, dy+dh,
                               fill=base, outline="")
        # top highlight stripe
        self.create_rectangle(cx-dw//2, dy,
                               cx+dw//2, dy+dh//3,
                               fill=hi, outline="")
        # bottom shadow
        self.create_rectangle(cx-dw//2+2, dy+dh-3,
                               cx+dw//2-2, dy+dh,
                               fill="#111111", outline="")
        # left edge
        self.create_line(cx-dw//2, dy, cx-dw//2, dy+dh, fill=hi, width=2)

        # pixel notch decorations
        for ny in range(dy+4, dy+dh-2, 6):
            self.create_rectangle(cx-dw//2,   ny, cx-dw//2+3, ny+3,
                                   fill=P["bg"], outline="")
            self.create_rectangle(cx+dw//2-3, ny, cx+dw//2,   ny+3,
                                   fill=P["bg"], outline="")

        # disk number
        self.create_text(cx, dy+dh//2, text=str(disk),
                         fill=P["white"], font=FNTB(9), anchor="center")

        # locked border
        if locked:
            self.create_rectangle(cx-dw//2, dy, cx+dw//2, dy+dh,
                                   outline=P["red"], fill="", width=2)
            self.create_text(cx+dw//2-8, dy+3, text="X",
                             fill=P["red"], font=FNTB(8), anchor="center")

        # flying glow rings
        if flying:
            for gi in (10, 6, 2):
                self.create_rectangle(cx-dw//2-gi, dy-gi,
                                       cx+dw//2+gi, dy+dh+gi,
                                       outline=hi, fill="", width=1)

    def _draw_solved(self, W, H, sx, sy):
        self.create_rectangle(W//2-180, H//2-70,
                               W//2+180, H//2+85,
                               fill=P["panel"], outline=P["yellow"], width=3)
        tick = int(time.time() * 4)
        col  = P["yellow"] if tick % 2 == 0 else P["accent"]
        self.create_text(W//2, H//2-38, text="*  SOLVED!  *",
                         fill=col, font=FNTB(20), anchor="center")
        self.create_text(W//2, H//2+2,
                         text=f"{self.state.moves} moves  /  optimal {self.state.optimal()}",
                         fill=P["text"], font=FNTB(10), anchor="center")
        eff = "PERFECT!" if self.state.moves == self.state.optimal() else "WELL DONE!"
        self.create_text(W//2, H//2+32, text=eff,
                         fill=P["green"], font=FNTB(13), anchor="center")

    # ── fly animation ─────────────────────────────────────
    def _launch_fly(self, disk, src, dst, pegs_before):
        W = max(self.winfo_width(), 460)
        H = max(self.winfo_height(), 400)
        PAD   = 32
        col_W = (W - PAD*2) / 3
        peg_xs = [PAD + col_W*(k+0.5) for k in range(3)]
        base_y = H - 68
        dh     = max(14, min(30, (int((H-100)*0.78)-16) // (self.state.n+2)))

        j_src = len(pegs_before[src])
        self._fly_disk  = disk
        self._fly_x     = peg_xs[src]
        self._fly_y     = base_y - j_src*(dh+2)
        self._fly_tx    = peg_xs[dst]
        self._fly_ty    = base_y - len(self.state.pegs[dst])*(dh+2)
        self._fly_steps = self._fly_total = 14

    def _step_fly(self):
        if self._fly_steps <= 0:
            self._fly_disk = None
            return
        t = 1.0 - self._fly_steps / self._fly_total
        t = t*t*(3 - 2*t)   # smooth step
        self._fly_x += (self._fly_tx - self._fly_x) * 0.2
        self._fly_y += (self._fly_ty - self._fly_y) * 0.18
        self._fly_y -= math.sin(t * math.pi) * 9  # arc
        self._fly_steps -= 1
        if self._fly_steps == 0:
            self._fly_disk = None

    # ── click ─────────────────────────────────────────────
    def _click(self, event):
        if not self.interactive: return
        if self.state.solved:    return
        if self._fly_disk is not None: return

        W     = max(self.winfo_width(), 460)
        PAD   = 32
        col_W = (W - PAD*2) / 3
        peg_xs = [PAD + col_W*(k+0.5) for k in range(3)]

        clicked = None
        for k, px in enumerate(peg_xs):
            if abs(event.x - px) < col_W/2:
                clicked = k
                break
        if clicked is None:
            return

        if self.selected is None:
            if not self.state.pegs[clicked]:
                self._bad(); return
            td = self.state.pegs[clicked][-1]
            if td in self.state.locked:
                self._bad()
                if self.on_move:
                    self.on_move(-1, -1, False, "DISK LOCKED!")
                return
            self.selected = clicked
            if self.on_select:
                self.on_select(clicked)
        else:
            src, dst = self.selected, clicked
            self.selected = None
            if src == dst:
                return
            pb = [list(p) for p in self.state.pegs]
            ok, msg = self.state.do_move(src, dst)
            if ok:
                td  = self.state.pegs[dst][-1]
                col = DISK_PAL[(td-1) % len(DISK_PAL)][0]
                W2  = max(self.winfo_width(),  460)
                H2  = max(self.winfo_height(), 400)
                PAD2  = 32
                cW2   = (W2 - PAD2*2) / 3
                px_d  = PAD2 + cW2*(dst+0.5)
                base2 = H2 - 68
                dh2   = max(14, min(30, (int((H2-100)*0.78)-16)//(self.state.n+2)))
                by    = base2 - len(self.state.pegs[dst])*(dh2+2)
                self.parts.burst(px_d, by, col, n=18, speed=4.0)
                self.parts.burst(px_d, by, P["white"], n=6, speed=3.0)
                self._launch_fly(td, src, dst, pb)
                if self.state.solved:
                    self.parts.explosion(W2//2, H2//2,
                        [P["yellow"], P["accent"], P["pink"],
                         P["green"],  P["purple"]], n=120)
            else:
                self._bad()
                self.shaker.trigger(5)
            if self.on_move:
                self.on_move(src, dst, ok, msg)

    def _bad(self):
        self._flash_col = P["red"]
        self._flash_t   = 9
        self.shaker.trigger(4)

    def set_interactive(self, v):
        self.interactive = v

    def key_press(self, peg_idx):
        """Trigger a peg selection/move via keyboard (0=A, 1=B, 2=C)."""
        if not self.interactive: return
        if self.state.solved:    return
        if self._fly_disk is not None: return
        # Simulate a click on peg peg_idx
        class _FakeEvent:
            pass
        W     = max(self.winfo_width(), 460)
        PAD   = 32
        col_W = (W - PAD*2) / 3
        ev = _FakeEvent()
        ev.x = PAD + col_W*(peg_idx + 0.5)
        self._click(ev)


# ===================================================================
#  PIXEL BUTTON  (with optional canvas-drawn icon left of text)
# ===================================================================
class PixBtn(tk.Frame):
    """
    True pixel-art button:
    - 4px block outer border in accent color
    - 4px inner dark body
    - Checkerboard dither highlight strip on top/left when hovered
    - Pressed state shifts content 3px down-right (chunky press feel)
    - Large enough icon painted with px() blocks
    """
    def __init__(self, parent, text, color, command,
                 w=180, h=44, font_size=11, icon=None):
        super().__init__(parent, bg=P["bg"], cursor="hand2")
        self._text    = text
        self._color   = color
        self._cmd     = command
        self._bw      = w
        self._bh      = h
        self._fs      = font_size
        self._icon    = icon
        self._hovered = False
        self._clicked = False
        self._cv = tk.Canvas(self, width=w, height=h,
                             bg=P["bg"], highlightthickness=0, cursor="hand2")
        self._cv.pack()
        for wgt in (self, self._cv):
            wgt.bind("<Enter>",           self._enter)
            wgt.bind("<Leave>",           self._leave)
            wgt.bind("<ButtonPress-1>",   self._btn_down)
            wgt.bind("<ButtonRelease-1>", self._btn_up)
        self._draw()

    def _draw(self):
        c   = self._cv
        c.delete("all")
        if not hasattr(c, "_icon_refs"): c._icon_refs = []
        c._icon_refs.clear()

        w, h = self._bw, self._bh
        col  = self._color
        B    = 4
        off  = B if self._clicked else 0

        if _PIL:
            # ── Pillow-rendered pixel-art button ──────────────
            sc  = 1
            art = PixelArt(w, h, scale=sc, bg=P["bg"])
            lB  = B

            # drop shadow
            if not self._clicked:
                art.rect(lB//2, lB//2, w-1, h-1, P["bg2"])

            # outer border block
            art.rect(off, off, w-lB*2+off, h-lB*2+off, col)

            # inner body
            body = P["dark2"] if self._hovered else P["panel"]
            art.rect(off+lB, off+lB, w-lB*3+off, h-lB*3+off, body)

            # dither highlight (top + left inner edge)
            if self._hovered and not self._clicked:
                for xx in range(off+lB, w-lB*3+off, 4):
                    art.pixel(xx,   off+lB, col)
                    art.pixel(xx+1, off+lB, col)
                for yy in range(off+lB, h-lB*3+off, 4):
                    art.pixel(off+lB, yy,   col)
                    art.pixel(off+lB, yy+1, col)

            # inner bottom/right shadow
            art.hline(off+lB, h-lB*3+off, w-lB*3+off, P["bg"])
            art.vline(w-lB*3+off, off+lB, h-lB*3+off, P["bg"])

            # corner pixel accents (4 corners)
            cc = P["white"] if self._hovered else col
            for ax, ay in [(off, off), (w-lB*2+off-1, off),
                           (off, h-lB*2+off-1), (w-lB*2+off-1, h-lB*2+off-1)]:
                art.pixel(ax, ay, cc)

            photo = art.photo()
            c._icon_refs.append(photo)
            c.create_image(0, 0, image=photo, anchor="nw")

            # text + icon on top
            tc     = P["white"] if self._hovered else col
            cx_mid = w // 2 + off//2
            cy_mid = h // 2 + off//2 - lB

            if self._icon:
                icon_sz = min(h - lB*6, 28)
                icon_sz = max(14, (icon_sz // 4) * 4)
                ix_x = off + lB + icon_sz // 2 + 4
                draw_icon(c, self._icon, ix_x, cy_mid, size=icon_sz, color=tc)
                tx = off + lB + icon_sz + 10
                c.create_text(tx, cy_mid, text=self._text,
                              fill=tc, font=FNTB(self._fs), anchor="w")
            else:
                c.create_text(cx_mid, cy_mid, text=self._text,
                              fill=tc, font=FNTB(self._fs), anchor="center")

        else:
            # ── Canvas fallback ───────────────────────────────
            tc = P["white"] if self._hovered else col
            if not self._clicked:
                c.create_rectangle(B, B, w, h, fill=P["bg2"], outline="")
            bx0, by0 = off, off
            bx1, by1 = off+w-B*2, off+h-B*2
            c.create_rectangle(bx0, by0, bx1, by1, fill=col, outline="")
            ix0, iy0 = bx0+B, by0+B
            ix1, iy1 = bx1-B, by1-B
            c.create_rectangle(ix0, iy0, ix1, iy1,
                               fill=P["dark2"] if self._hovered else P["panel"],
                               outline="")
            cx_mid = (ix0+ix1)//2
            cy_mid = (iy0+iy1)//2
            if self._icon:
                icon_sz = max(12, min(h-B*4-8, 24))
                draw_icon(c, self._icon, ix0+icon_sz//2+6, cy_mid, size=icon_sz, color=tc)
                c.create_text(ix0+icon_sz+12, cy_mid, text=self._text,
                              fill=tc, font=FNTB(self._fs), anchor="w")
            else:
                c.create_text(cx_mid, cy_mid, text=self._text,
                              fill=tc, font=FNTB(self._fs), anchor="center")

    def _enter(self, e):    self._hovered=True;  self._draw()
    def _leave(self, e):    self._hovered=False; self._clicked=False; self._draw()
    def _btn_down(self, e): self._clicked=True;  self._draw()
    def _btn_up(self,   e):
        self._clicked=False; self._draw()
        if self._cmd: self._cmd()


# ═══════════════════════════════════════════════════════════
#  PIXEL ENTRY
# ═══════════════════════════════════════════════════════════
class PixEntry(tk.Frame):
    """Canvas-bordered pixel-art text entry."""
    def __init__(self, parent, width=20, default=""):
        super().__init__(parent, bg=P["bg"])
        B = 3   # border block size
        # outer frame acts as pixel border
        self._border = tk.Frame(self, bg=P["accent"])
        self._border.pack(padx=0, pady=0)
        inner = tk.Frame(self._border, bg=P["panel"])
        inner.pack(padx=B, pady=B)
        self._e = tk.Entry(inner,
                           bg=P["panel"], fg=P["accent"],
                           insertbackground=P["accent"],
                           font=FNTB(12), relief="flat", width=width,
                           highlightthickness=0,
                           selectbackground=P["accent"],
                           selectforeground=P["bg"])
        self._e.pack(padx=6, pady=4)
        self._e.insert(0, default)
        # focus changes border color
        self._e.bind("<FocusIn>",  lambda e: self._border.config(bg=P["pink"]))
        self._e.bind("<FocusOut>", lambda e: self._border.config(bg=P["accent"]))

    def get(self):
        return self._e.get()

    def pack(self, **kw):
        super().pack(**kw)
        return self

    def pack_configure(self, **kw):
        super().pack_configure(**kw)

    def ipady(self, v):
        self._e.config(font=FNTB(12))


# ═══════════════════════════════════════════════════════════
#  SHARED WIDGETS
# ═══════════════════════════════════════════════════════════
def disk_selector(parent, var):
    """Canvas-drawn pixel-art disk count buttons."""
    f   = tk.Frame(parent, bg=P["bg"])
    cvs = []
    BW, BH = 44, 44
    B = 3

    def draw_btn(cv, n, hovered=False):
        cv.delete("all")
        sel = (n == var.get())
        col = P["accent"] if sel else (P["pink"] if hovered else P["muted"])
        # outer border
        cv.create_rectangle(0, 0, BW, BH, fill=col, outline="")
        # inner body
        cv.create_rectangle(B, B, BW-B, BH-B,
                            fill=P["bg"] if sel else P["panel"], outline="")
        # dither corners if selected
        if sel:
            for x2,y2 in [(B,B),(BW-B-2,B),(B,BH-B-2),(BW-B-2,BH-B-2)]:
                cv.create_rectangle(x2,y2,x2+2,y2+2,fill=col,outline="")
        # number
        cv.create_text(BW//2, BH//2, text=str(n),
                       fill=P["bg"] if sel else col,
                       font=FNTB(13))

    def make_btn(n):
        cv = tk.Canvas(f, width=BW, height=BH,
                       bg=P["bg"], highlightthickness=0, cursor="hand2")
        cv.pack(side="left", padx=3)
        draw_btn(cv, n)

        def on_click(e, _n=n, _cv=cv):
            var.set(_n)
            for c2, num in cvs:
                draw_btn(c2, num)
        def on_enter(e, _n=n, _cv=cv):
            if _n != var.get(): draw_btn(_cv, _n, hovered=True)
        def on_leave(e, _n=n, _cv=cv):
            draw_btn(_cv, _n)

        cv.bind("<Button-1>", on_click)
        cv.bind("<Enter>",    on_enter)
        cv.bind("<Leave>",    on_leave)
        cvs.append((cv, n))

    for n in range(3, 9):
        make_btn(n)
    return f

def mode_selector(parent, var):
    """Canvas pixel-art mode tabs."""
    f    = tk.Frame(parent, bg=P["bg"])
    opts = [("CLASSIC","classic",P["accent"]),
            ("CHAOS",  "chaos",  P["orange"]),
            ("BLITZ",  "blitz",  P["pink"])]
    cvs  = []
    TW, TH, B = 110, 46, 4

    def draw_tab(cv, label, val, col, hovered=False):
        cv.delete("all")
        sel = (val == var.get())
        bc  = col
        body = P["bg"] if sel else (P["dark2"] if hovered else P["panel"])
        # border block
        cv.create_rectangle(0, 0, TW, TH, fill=bc, outline="")
        cv.create_rectangle(B, B, TW-B, TH-B, fill=body, outline="")
        # dither top strip when selected
        if sel:
            for xx in range(B, TW-B, 6):
                cv.create_rectangle(xx, B, xx+3, B+3, fill=bc, outline="")
        # bottom glow line
        cv.create_rectangle(B, TH-B-2, TW-B, TH-B, fill=bc, outline="")
        # label
        tc = P["bg"] if (sel and not hovered) else bc
        cv.create_text(TW//2, TH//2, text=label,
                       fill=P["white"] if sel else bc,
                       font=FNTB(11))

    def make_tab(label, val, col):
        cv = tk.Canvas(f, width=TW, height=TH,
                       bg=P["bg"], highlightthickness=0, cursor="hand2")
        cv.pack(side="left", padx=4)
        draw_tab(cv, label, val, col)

        def on_click(e, _v=val):
            var.set(_v)
            for c2, lbl2, v2, col2 in cvs:
                draw_tab(c2, lbl2, v2, col2)
        def on_enter(e, _cv=cv, _lbl=label, _v=val, _c=col):
            if _v != var.get(): draw_tab(_cv, _lbl, _v, _c, hovered=True)
        def on_leave(e, _cv=cv, _lbl=label, _v=val, _c=col):
            draw_tab(_cv, _lbl, _v, _c)

        cv.bind("<Button-1>", on_click)
        cv.bind("<Enter>",    on_enter)
        cv.bind("<Leave>",    on_leave)
        cvs.append((cv, label, val, col))

    for label, val, col in opts:
        make_tab(label, val, col)
    return f

def header_bar(parent, title, color, back_cmd):
    """Pixel-art header: 4px color bar top, chunky BACK btn, bold title."""
    f  = tk.Frame(parent, bg=P["dark1"])
    # top color bar (4px thick pixel strip)
    tk.Frame(f, bg=color, height=4).pack(fill="x", side="top")
    inner = tk.Frame(f, bg=P["dark1"])
    inner.pack(fill="x", side="top")

    # BACK button — canvas drawn, pixel bordered
    BW, BH = 78, 36
    B = 3
    bcv = tk.Canvas(inner, width=BW, height=BH, bg=P["dark1"],
                    highlightthickness=0, cursor="hand2")
    bcv.pack(side="left", padx=8, pady=6)

    def _draw_back(hover=False):
        bcv.delete("all")
        c = P["white"] if hover else P["muted"]
        bg2 = P["dark2"] if hover else P["dark1"]
        # border
        bcv.create_rectangle(0, 0, BW, BH, fill=c, outline="")
        bcv.create_rectangle(B, B, BW-B, BH-B, fill=bg2, outline="")
        if hover:
            for xx in range(B, BW-B, 6):
                bcv.create_rectangle(xx, B, xx+2, B+2, fill=c, outline="")
        draw_icon(bcv, "back", 18, BH//2, size=18, color=c)
        bcv.create_text(BW//2+8, BH//2, text="BACK",
                        fill=c, font=FNTB(8), anchor="center")

    _draw_back(False)
    bcv.bind("<Enter>",    lambda e: _draw_back(True))
    bcv.bind("<Leave>",    lambda e: _draw_back(False))
    bcv.bind("<Button-1>", lambda e: back_cmd())

    # title text
    tk.Label(inner, text=title, bg=P["dark1"], fg=color,
             font=FNTB(16), pady=6).pack(side="left", padx=14)

    # right-side accent strip (decorative pixel block)
    tk.Frame(inner, bg=color, width=6).pack(side="right", fill="y", padx=4)

    # bottom pixel border
    tk.Frame(f, bg=color, height=4).pack(fill="x", side="bottom")
    return f


# ═══════════════════════════════════════════════════════════
#  SCREEN BASE
# ═══════════════════════════════════════════════════════════
class Screen(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=P["bg"])

    def on_destroy(self):
        pass

    def destroy(self):
        self.on_destroy()
        super().destroy()


# ═══════════════════════════════════════════════════════════
#  SCREEN: MAIN MENU
# ═══════════════════════════════════════════════════════════
class MenuScreen(Screen):
    def __init__(self, master):
        super().__init__(master)
        self._tid   = None
        self._tick  = 0
        self._parts = Particles()

        self.tc = tk.Canvas(self, bg=P["bg"], highlightthickness=0, height=240)
        self.tc.pack(fill="x")

        tk.Frame(self, bg=P["accent"], height=3).pack(fill="x")

        tk.Label(self, text="SELECT  GAME  TYPE",
                 bg=P["bg"], fg=P["muted"], font=FNTB(11)).pack(pady=(16,10))

        row = tk.Frame(self, bg=P["bg"])
        row.pack(pady=6)
        PixBtn(row, "SOLO",   P["accent"],  master.go_solo,   w=190, h=56, font_size=12, icon="solo").pack(side="left", padx=8)
        PixBtn(row, "VS BOT", P["purple"],  master.go_vsbot,  w=190, h=56, font_size=12, icon="robot").pack(side="left", padx=8)
        PixBtn(row, "MULTI",    P["pink"],    master.go_mp,     w=190, h=56, font_size=12, icon="multi").pack(side="left", padx=8)

        row2 = tk.Frame(self, bg=P["bg"])
        row2.pack(pady=10)
        PixBtn(row2,"SCORES", P["yellow"],  master.go_scores, w=180, h=42, font_size=11, icon="scores").pack(side="left", padx=10)

        tk.Label(self,
                 text="CLICK PEG TO LIFT/PLACE DISK  |  NO LARGER DISK ON SMALLER",
                 bg=P["bg"], fg=P["muted"], font=FNT(8)).pack(pady=(14,2))
        tk.Label(self,
                 text=f"LAN MULTIPLAYER  PORT {NET_PORT}  |  SCORES SAVED TO {SCORES_FILE}",
                 bg=P["bg"], fg=P["border"], font=FNT(7)).pack(pady=(0,8))

        self._loop()

    def _loop(self):
        self._tick += 1
        self._parts.update()
        self._draw_title()
        self._tid = self.after(40, self._loop)

    def _draw_title(self):
        c = self.tc
        c.delete("all")
        W = max(c.winfo_width(), 800)
        H = 240

        c.create_rectangle(0, 0, W, H, fill=P["bg"], outline="")

        # pixel grid
        for gx in range(0, W, 20):
            c.create_line(gx, 0, gx, H, fill=P["grid"])
        for gy in range(0, H, 20):
            c.create_line(0, gy, W, gy, fill=P["grid"])

        # scanlines
        for y in range(0, H, 4):
            c.create_line(0, y, W, y, fill=P["bg"], stipple="gray25")

        # animated neon bar at bottom
        bw = 60
        for i in range(-1, W//bw + 2):
            x = (i * bw + (self._tick * 2) % bw) - bw
            shade = P["accent"] if i % 2 == 0 else P["pink"]
            c.create_rectangle(x, H-5, x+bw//2, H, fill=shade, outline="")

        # CRT corner brackets
        for ox, oy, fx, fy in [(0,0,1,1),(W,0,-1,1),(0,H,1,-1),(W,H,-1,-1)]:
            for d in range(0, 30, 3):
                c.create_line(ox, oy+fy*d, ox+fx*28, oy+fy*d,
                              fill=P["accent"], width=1)
                c.create_line(ox+fx*d, oy, ox+fx*d, oy+fy*28,
                              fill=P["accent"], width=1)

        # title shadow then main
        tx, ty = W//2, 78
        c.create_text(tx+4, ty+4, text="TOWER  OF  HANOI",
                      font=("Courier New", 38, "bold"),
                      fill=P["dark1"], anchor="center")
        c.create_text(tx, ty, text="TOWER  OF  HANOI",
                      font=("Courier New", 38, "bold"),
                      fill=P["accent"], anchor="center")

        # subtitle flicker
        flicker = P["pink"] if (self._tick//6) % 2 == 0 else P["yellow"]
        c.create_text(tx, ty+52, text="P I X E L   E D I T I O N",
                      font=FNTB(13), fill=flicker, anchor="center")

        # animated pixel disk stack
        disk_max = 180
        for i, (base, hi) in enumerate(DISK_PAL[:6]):
            dw   = disk_max - i*24
            dx   = tx - dw//2
            dy_d = ty + 90 + i*10
            bob  = int(math.sin(self._tick*0.08 + i*0.7) * 3)
            c.create_rectangle(dx, dy_d+bob, dx+dw, dy_d+bob+9,
                               fill=base, outline="")
            c.create_rectangle(dx, dy_d+bob, dx+dw, dy_d+bob+3,
                               fill=hi, outline="")

        # random sparks
        if random.random() < 0.15:
            self._parts.burst(
                random.randint(W//4, 3*W//4),
                random.randint(50, 160),
                random.choice([P["accent"], P["yellow"], P["pink"]]),
                n=6, speed=3.0
            )
        self._parts.draw(c)

    def on_destroy(self):
        if self._tid:
            self.after_cancel(self._tid)


# ═══════════════════════════════════════════════════════════
#  SCREEN: SOLO SETUP
# ═══════════════════════════════════════════════════════════
class SoloSetup(Screen):
    def __init__(self, master):
        super().__init__(master)
        self.dvar = tk.IntVar(value=4)
        self.mvar = tk.StringVar(value="classic")
        header_bar(self, "SOLO  GAME  SETUP", P["accent"],
                   master.go_menu).pack(fill="x")
        body = tk.Frame(self, bg=P["bg"])
        body.pack(expand=True)

        tk.Label(body, text="YOUR NAME", bg=P["bg"],
                 fg=P["muted"], font=FNTB(9)).pack(pady=(28,4))
        self.name_e = PixEntry(body, width=24, default="PLAYER1")
        self.name_e.pack(pady=2)

        tk.Label(body, text="NUMBER OF DISKS", bg=P["bg"],
                 fg=P["muted"], font=FNTB(9)).pack(pady=(18,4))
        disk_selector(body, self.dvar).pack()

        tk.Label(body, text="GAME MODE", bg=P["bg"],
                 fg=P["muted"], font=FNTB(9)).pack(pady=(18,4))
        mode_selector(body, self.mvar).pack()

        tk.Frame(body, bg=P["border"], height=2).pack(fill="x", pady=22)
        PixBtn(body, "START GAME", P["green"],
               self._start, w=220, h=54, font_size=13, icon="play").pack(pady=4)

    def _get_name(self):
        return self.name_e.get().strip().upper() or "PLAYER1"

    def _start(self):
        n = self._get_name()
        self.master.start_solo(n, self.dvar.get(), self.mvar.get())


# ═══════════════════════════════════════════════════════════
#  SCREEN: MULTIPLAYER SETUP
# ═══════════════════════════════════════════════════════════
class MPSetup(Screen):
    def __init__(self, master):
        super().__init__(master)
        self.dvar = tk.IntVar(value=4)
        self.mvar = tk.StringVar(value="classic")
        header_bar(self, "MULTIPLAYER  SETUP", P["pink"],
                   master.go_menu).pack(fill="x")

        # scrollable body
        body = tk.Frame(self, bg=P["bg"])
        body.pack(expand=True)

        # ── IP info panel ─────────────────────────────────
        info = tk.Frame(body, bg=P["dark1"])
        info.pack(pady=(14,4), padx=30, fill="x")

        # Get all local IPs
        my_ips = get_all_local_ips()
        ip_str = "  |  ".join(my_ips)

        tk.Label(info, text="YOUR IP ADDRESSES:", bg=P["dark1"],
                 fg=P["muted"], font=FNTB(8), pady=4).pack()
        ip_lbl = tk.Label(info, text=ip_str, bg=P["dark1"],
                          fg=P["pink"], font=FNTB(12), pady=4)
        ip_lbl.pack()
        # click to copy
        def copy_ip(e):
            master.clipboard_clear()
            master.clipboard_append(my_ips[0])
            ip_lbl.config(text=f"COPIED: {my_ips[0]}")
            master.after(1500, lambda: ip_lbl.config(text=ip_str))
        ip_lbl.bind("<Button-1>", copy_ip)
        ip_lbl.config(cursor="hand2")
        tk.Label(info, text="[click IP to copy]  Give this to your opponent",
                 bg=P["dark1"], fg=P["border"], font=FNT(8), pady=3).pack()

        # ── Form fields ───────────────────────────────────
        # Name
        tk.Label(body, text="YOUR NAME", bg=P["bg"],
                 fg=P["muted"], font=FNTB(9)).pack(pady=(10,3))
        self.name_e = PixEntry(body, width=22, default="PLAYER1")
        self.name_e.pack(pady=2)

        # Host IP + Port on same row
        row_ip = tk.Frame(body, bg=P["bg"])
        row_ip.pack(pady=(10,0))
        tk.Label(row_ip, text="HOST IP:", bg=P["bg"],
                 fg=P["muted"], font=FNTB(9)).pack(side="left", padx=(0,6))
        self.ip_e = PixEntry(row_ip, width=18, default="")
        self.ip_e.pack(side="left", )
        tk.Label(row_ip, text="  PORT:", bg=P["bg"],
                 fg=P["muted"], font=FNTB(9)).pack(side="left", padx=(10,6))
        self.port_e = PixEntry(row_ip, width=6, default=str(NET_PORT))
        self.port_e.pack(side="left", ipady=8)

        tk.Label(body, text="Leave HOST IP blank if YOU are hosting",
                 bg=P["bg"], fg=P["border"], font=FNT(8)).pack(pady=(2,8))

        # Disks + mode
        tk.Label(body, text="NUMBER OF DISKS", bg=P["bg"],
                 fg=P["muted"], font=FNTB(9)).pack(pady=(4,3))
        disk_selector(body, self.dvar).pack()
        tk.Label(body, text="GAME MODE", bg=P["bg"],
                 fg=P["muted"], font=FNTB(9)).pack(pady=(10,3))
        mode_selector(body, self.mvar).pack()

        # Status bar
        self.status = tk.Label(body, text="", bg=P["bg"],
                               fg=P["yellow"], font=FNTB(10),
                               wraplength=500)
        self.status.pack(pady=8)

        br = tk.Frame(body, bg=P["bg"])
        br.pack(pady=4)
        PixBtn(br,"HOST GAME", P["accent"], self._host,
               w=180, h=46, icon="multi").pack(side="left", padx=8)
        PixBtn(br,"JOIN GAME", P["pink"],   self._join,
               w=180, h=46, icon="play").pack(side="left", padx=8)

    def _get_name(self):
        return self.name_e.get().strip().upper() or "PLAYER1"

    def _port(self):
        try:
            p = int(self.port_e.get().strip())
            if 1024 <= p <= 65535:
                return p
        except Exception:
            pass
        return NET_PORT

    def _host(self):
        port = self._port()
        self.status.config(
            text=f"STARTING SERVER ON PORT {port}...", fg=P["yellow"])
        self.update()
        self.master.mp_host(self._get_name(), self.dvar.get(),
                            self.mvar.get(), self.status, port)

    def _join(self):
        ip = self.ip_e.get().strip()
        if not ip:
            self.status.config(text="ENTER HOST IP TO JOIN!", fg=P["red"])
            return
        port = self._port()
        self.status.config(
            text=f"CONNECTING TO {ip}:{port} ...", fg=P["yellow"])
        self.update()
        self.master.mp_join(self._get_name(), ip, self.dvar.get(),
                            self.mvar.get(), self.status, port)


# ═══════════════════════════════════════════════════════════
#  HUD BAR
# ═══════════════════════════════════════════════════════════
class HudBar(tk.Frame):
    def __init__(self, parent, players, mode, back_cb, restart_cb):
        super().__init__(parent, bg=P["panel"])
        def _make_hud_btn(parent, icon_id, label, color, cmd, side="left"):
            cv = tk.Canvas(parent, width=72, height=34,
                           bg=P["panel"], highlightthickness=0, cursor="hand2")
            cv.pack(side=side, padx=6, pady=6)
            def _draw(h=False):
                cv.delete("all")
                c = color if h else P["muted"]
                cv.create_rectangle(1, 1, 71, 33, outline=c, fill="", width=1)
                draw_icon(cv, icon_id, 14, 17, size=16, color=c)
                cv.create_text(44, 17, text=label, fill=c, font=FNTB(7), anchor="center")
            _draw(False)
            cv.bind("<Enter>",    lambda e: _draw(True))
            cv.bind("<Leave>",    lambda e: _draw(False))
            cv.bind("<Button-1>", lambda e: cmd())
            return cv
        _make_hud_btn(self, "back",    "MENU",    P["accent"], back_cb,    side="left")

        mode_map = {"classic": ("CLASSIC", P["accent"]),
                    "chaos":   ("CHAOS",   P["orange"])}
        lbl, col = mode_map.get(mode, ("MODE", P["accent"]))
        tk.Label(self, text=lbl, bg=P["panel"],
                 fg=col, font=FNTB(14)).pack(side="left", padx=14)

        self.stat_labels = {}
        for name in players:
            f = tk.Frame(self, bg=P["dark1"], padx=12, pady=4)
            f.pack(side="left", padx=8)
            tk.Label(f, text=name, bg=P["dark1"],
                     fg=P["yellow"], font=FNTB(10)).pack()
            mv = tk.Label(f, text="MOVES: 0", bg=P["dark1"],
                          fg=P["text"], font=FNTB(9))
            mv.pack()
            tm = tk.Label(f, text="TIME: --", bg=P["dark1"],
                          fg=P["accent"], font=FNTB(9))
            tm.pack()
            self.stat_labels[name] = (mv, tm)

        _make_hud_btn(self, "restart", "RESTART", P["accent"], restart_cb, side="right")
        tk.Frame(self, bg=P["accent"], height=2).pack(side="bottom", fill="x")

    def update_stats(self, name, moves, secs):
        if name in self.stat_labels:
            mv, tm = self.stat_labels[name]
            mv.config(text=f"MOVES: {moves}")
            if secs is not None:
                tm.config(text=f"TIME: {secs:.1f}s")


# ═══════════════════════════════════════════════════════════
#  SCREEN: SOLO GAME
# ═══════════════════════════════════════════════════════════
class SoloGame(Screen):
    def __init__(self, master, name, disks, mode):
        super().__init__(master)
        self.name  = name
        self.disks = disks
        self.mode  = mode
        self.state = HanoiState(disks)
        self.t0    = None
        self._cid  = None
        self._tid  = None
        self._build()
        if mode == "chaos":
            self._sched_chaos()

    def _build(self):
        self.hud = HudBar(self, [self.name], self.mode,
                          self._quit, self._restart)
        self.hud.pack(fill="x")

        self.msg = tk.Label(self, text="CLICK A PEG TO LIFT A DISK",
                            bg=P["bg2"], fg=P["muted"],
                            font=FNTB(10), pady=6)
        self.msg.pack(fill="x")

        self.board = BoardCanvas(self, self.state, interactive=True,
                                  label=f"{self.name}  |  DISKS:{self.disks}  |  MOVE ALL TO PEG C")
        self.board.pack(fill="both", expand=True, padx=12, pady=8)
        self.board.on_move = self._on_move

        hints = {
            "classic": "CLASSIC  |  2^n-1 OPTIMAL MOVES  |  A/S/D = PEG A/B/C  |  LARGER NEVER ON SMALLER",
            "chaos":   "CHAOS MODE  |  DISKS LOCK  |  PEGS BLOCK RANDOMLY  |  A/S/D KEYS = PEGS A/B/C"
        }
        tk.Label(self, text=hints.get(self.mode, ""),
                 bg=P["bg"], fg=P["border"], font=FNT(8)).pack(pady=(0,4))

        self._bind_keys(self.board)
        self._tid = self.after(100, self._tick)

    def _bind_keys(self, board):
        """Bind A/S/D (and Q/W/E) to pegs A/B/C. ESC deselects."""
        def _key(e):
            k = e.keysym.lower()
            if   k in ("a","q"):  board.key_press(0)
            elif k in ("s","w"):  board.key_press(1)
            elif k in ("d","e"):  board.key_press(2)
            elif k == "escape":   board.selected = None
        self.master.bind("<Key>", _key)
        self.master.focus_set()

    def _on_move(self, src, dst, ok, msg):
        if src == -1:
            self.msg.config(text=f"! {msg}", fg=P["red"])
            return
        if ok:
            if self.t0 is None:
                self.t0 = time.time()
            self.msg.config(
                text=f"MOVED  {['A','B','C'][src]}  >>  {['A','B','C'][dst]}",
                fg=P["green"])
            if self.state.solved:
                self._on_solved()
        else:
            self.msg.config(text=f"! {msg}", fg=P["red"])

    def _on_solved(self):
        if self._cid:
            self.after_cancel(self._cid)
        elapsed = time.time() - (self.t0 or time.time())
        score   = self.master.scores.add(
            self.mode, self.name, self.disks, self.state.moves, elapsed)
        self.msg.config(
            text=f"* SOLVED!  {self.state.moves} MOVES  {elapsed:.1f}s  SCORE: {score:,}",
            fg=P["yellow"])

    def _tick(self):
        t = (time.time()-self.t0) if self.t0 and not self.state.solved else None
        self.hud.update_stats(self.name, self.state.moves, t)
        self._tid = self.after(100, self._tick)

    def _sched_chaos(self):
        self._cid = self.after(random.randint(7000,16000), self._chaos)

    def _chaos(self):
        if self.state.solved:
            return
        s  = self.state
        ev = random.choice(["lock","lock","block","unlock","unblock"])
        if ev == "lock":
            all_d = [d for p in s.pegs for d in p]
            if all_d:
                disk = random.choice(all_d)
                s.locked.add(disk)
                self.msg.config(text=f"! CHAOS: DISK {disk} LOCKED 5s!", fg=P["orange"])
                self.after(5000, lambda d=disk: s.locked.discard(d))
        elif ev == "block":
            empty = [k for k in range(3) if not s.pegs[k]]
            if empty:
                peg = random.choice(empty)
                s.blocked.add(peg)
                self.msg.config(text=f"! CHAOS: PEG {['A','B','C'][peg]} BLOCKED 6s!", fg=P["red"])
                self.after(6000, lambda p=peg: s.blocked.discard(p))
        elif ev == "unlock":
            s.locked.clear()
            self.msg.config(text="OK ALL DISKS UNLOCKED", fg=P["green"])
        elif ev == "unblock":
            s.blocked.clear()
            self.msg.config(text="OK ALL PEGS CLEARED", fg=P["green"])
        self._sched_chaos()

    def _quit(self):
        self.on_destroy()
        self.master.go_menu()

    def _restart(self):
        self.on_destroy()
        self.master.start_solo(self.name, self.disks, self.mode)

    def on_destroy(self):
        if self._cid: self.after_cancel(self._cid)
        if self._tid: self.after_cancel(self._tid)


# ═══════════════════════════════════════════════════════════
#  SCREEN: MULTIPLAYER GAME
# ═══════════════════════════════════════════════════════════
class MPGame(Screen):
    def __init__(self, master, my_name, opp_name,
                 disks, mode, net, is_host):
        super().__init__(master)
        self.my_name  = my_name
        self.opp_name = opp_name
        self.disks    = disks
        self.mode     = mode
        self.net      = net
        self.is_host  = is_host
        self.my_st    = HanoiState(disks)
        self.op_st    = HanoiState(disks)
        self.my_t0 = self.op_t0 = None
        self.my_t1 = self.op_t1 = None
        self._cid  = None
        self._tid  = None
        self.net.on_move_cb = self._net_in
        self._build()
        if mode == "chaos":
            self._sched_chaos()

    def _build(self):
        self.hud = HudBar(self, [self.my_name, self.opp_name],
                          self.mode, self._quit, self._restart)
        self.hud.pack(fill="x")

        self.msg = tk.Label(self, text="SOLVE YOUR BOARD FIRST!",
                            bg=P["bg2"], fg=P["muted"],
                            font=FNTB(10), pady=6)
        self.msg.pack(fill="x")

        boards = tk.Frame(self, bg=P["bg"])
        boards.pack(fill="both", expand=True, padx=8, pady=6)

        self.my_board = BoardCanvas(boards, self.my_st,
                                    interactive=True,
                                    label=f"YOU  {self.my_name}")
        self.my_board.pack(side="left", fill="both", expand=True, padx=(0,4))
        self.my_board.on_move   = self._my_move
        self.my_board.on_select = self._my_select

        self.op_board = BoardCanvas(boards, self.op_st,
                                    interactive=False,
                                    label=f"OPPONENT  {self.opp_name}")
        self.op_board.pack(side="right", fill="both", expand=True, padx=(4,0))

        tk.Label(self, text="A/S/D = PEG A/B/C  |  ESC = DESELECT  |  RACE YOUR OPPONENT!",
                 bg=P["bg"], fg=P["border"], font=FNT(8)).pack(pady=(0,3))

        self._bind_keys(self.my_board)
        self._tid = self.after(100, self._tick)

    def _bind_keys(self, board):
        def _key(e):
            k = e.keysym.lower()
            if   k in ("a","q"):  board.key_press(0)
            elif k in ("s","w"):  board.key_press(1)
            elif k in ("d","e"):  board.key_press(2)
            elif k == "escape":   board.selected = None
        self.master.bind("<Key>", _key)
        self.master.focus_set()

    def _my_move(self, src, dst, ok, msg):
        if src == -1:
            self.msg.config(text=f"! {msg}", fg=P["red"])
            return
        if ok:
            if self.my_t0 is None:
                self.my_t0 = time.time()
            self.net.send({"t":"mv","s":src,"d":dst})
            self.msg.config(
                text=f"YOU: {['A','B','C'][src]} >> {['A','B','C'][dst]}",
                fg=P["green"])
            if self.my_st.solved:
                self.my_t1 = time.time()
                self.net.send({"t":"done","m":self.my_st.moves,
                               "sec":round(self.my_t1-self.my_t0,1)})
                self._check_winner()
        else:
            self.msg.config(text=f"! {msg}", fg=P["red"])

    def _my_select(self, peg):
        """Broadcast to opponent that we lifted from peg."""
        self.net.send({"t": "sel", "p": peg})

    def _net_in(self, obj):
        self.after(0, lambda: self._handle(obj))

    def _handle(self, obj):
        t = obj.get("t")
        if t == "sel":
            # opponent lifted a disk — show ghost
            self.op_board.op_selected = obj.get("p")
        elif t == "mv":
            # opponent placed — clear ghost, trigger fly animation
            self.op_board.op_selected = None
            s, d = obj["s"], obj["d"]
            pegs_before = [list(p) for p in self.op_st.pegs]
            ok, _ = self.op_st.do_move(s, d)
            if ok:
                if self.op_t0 is None:
                    self.op_t0 = time.time()
                if self.op_st.pegs[d]:
                    disk = self.op_st.pegs[d][-1]
                    self.op_board._launch_fly(disk, s, d, pegs_before)
                # particle burst
                W2  = max(self.op_board.winfo_width(), 460)
                H2  = max(self.op_board.winfo_height(), 400)
                PAD = 32; cW2 = (W2-PAD*2)/3
                px  = PAD + cW2*(d+0.5)
                by  = H2 - 68
                dh  = max(14, min(30, (int((H2-100)*0.78)-16)//(self.op_st.n+2)))
                py  = by - len(self.op_st.pegs[d])*(dh+2)
                col = DISK_PAL[(disk-1) % len(DISK_PAL)][0] if self.op_st.pegs[d] else P["pink"]
                self.op_board.parts.burst(px, py, col, n=14, speed=3.5)
        elif t == "done":
            if self.op_t1 is None:
                self.op_t1 = time.time()
            self._check_winner()
        elif t == "name":
            self.opp_name = obj.get("n", self.opp_name)
            self.op_board.label = f"OPPONENT  {self.opp_name}"
        elif t == "chaos_lock":
            d = obj["d"]
            self.my_st.locked.add(d)
            self.msg.config(text=f"! OPP CHAOS: YOUR DISK {d} LOCKED!", fg=P["orange"])
            self.after(5000, lambda: self.my_st.locked.discard(d))
        elif t == "chaos_block":
            p = obj["p"]
            self.my_st.blocked.add(p)
            self.msg.config(text=f"! OPP CHAOS: YOUR PEG {['A','B','C'][p]} BLOCKED!", fg=P["red"])
            self.after(6000, lambda: self.my_st.blocked.discard(p))

    def _check_winner(self):
        md = self.my_st.solved
        od = self.op_st.solved
        if md and od:
            mt = (self.my_t1 or time.time()) - (self.my_t0 or time.time())
            ot = (self.op_t1 or time.time()) - (self.op_t0 or time.time())
            if self.my_st.moves < self.op_st.moves:
                w = f"* {self.my_name} WINS BY FEWER MOVES!"
            elif self.op_st.moves < self.my_st.moves:
                w = f"* {self.opp_name} WINS BY FEWER MOVES!"
            elif mt < ot:
                w = f"* {self.my_name} WINS BY TIME!"
            else:
                w = f"* {self.opp_name} WINS BY TIME!"
            self.msg.config(text=w, fg=P["yellow"])
        elif md:
            self.msg.config(text="* YOU SOLVED IT! WAITING FOR OPPONENT...", fg=P["yellow"])
        elif od:
            self.msg.config(text=f"! {self.opp_name} SOLVED FIRST! KEEP GOING!", fg=P["red"])

    def _tick(self):
        mt = (time.time()-self.my_t0) if self.my_t0 and not self.my_st.solved else None
        ot = (time.time()-self.op_t0) if self.op_t0 and not self.op_st.solved else None
        self.hud.update_stats(self.my_name,  self.my_st.moves, mt)
        self.hud.update_stats(self.opp_name, self.op_st.moves, ot)
        self._tid = self.after(100, self._tick)

    def _sched_chaos(self):
        self._cid = self.after(random.randint(10000,20000), self._chaos)

    def _chaos(self):
        if self.my_st.solved and self.op_st.solved:
            return
        if random.random() < 0.5:
            all_d = [d for p in self.op_st.pegs for d in p]
            if all_d:
                disk = random.choice(all_d)
                self.op_st.locked.add(disk)
                self.net.send({"t":"chaos_lock","d":disk})
                self.after(5000, lambda d=disk: self.op_st.locked.discard(d))
        else:
            empty = [k for k in range(3) if not self.op_st.pegs[k]]
            if empty:
                peg = random.choice(empty)
                self.op_st.blocked.add(peg)
                self.net.send({"t":"chaos_block","p":peg})
                self.after(6000, lambda p=peg: self.op_st.blocked.discard(p))
        self._sched_chaos()

    def _quit(self):
        self.on_destroy()
        self.master.go_menu()

    def _restart(self):
        self.on_destroy()
        self.master.go_menu()

    def on_destroy(self):
        if self._cid: self.after_cancel(self._cid)
        if self._tid: self.after_cancel(self._tid)
        try: self.net.close()
        except Exception: pass


# ═══════════════════════════════════════════════════════════
#  SCREEN: SCOREBOARD
# ═══════════════════════════════════════════════════════════
class ScoreScreen(Screen):
    def __init__(self, master):
        super().__init__(master)
        header_bar(self, "HALL  OF  LEGENDS", P["yellow"],
                   master.go_menu).pack(fill="x")

        tabs = tk.Frame(self, bg=P["bg"])
        tabs.pack(fill="x", padx=20, pady=10)
        for lbl, key, col in [("CLASSIC","classic",P["accent"]),
                                ("CHAOS",  "chaos",  P["orange"])]:
            tk.Button(tabs, text=lbl, font=FNTB(11),
                      bg=P["panel"], fg=col, relief="flat",
                      padx=18, pady=8, cursor="hand2",
                      command=lambda k=key: self._show(k)).pack(side="left", padx=4)

        self.body = tk.Frame(self, bg=P["bg"])
        self.body.pack(fill="both", expand=True, padx=20)
        self._show("classic")

    def _show(self, mode):
        for w in self.body.winfo_children():
            w.destroy()
        entries = self.master.scores.top(mode)
        if not entries:
            tk.Label(self.body, text="NO SCORES YET -- PLAY FIRST!",
                     bg=P["bg"], fg=P["muted"], font=FNTB(13)).pack(expand=True, pady=60)
            return

        cols = [("RNK",4),("NAME",16),("DISKS",5),("MOVES",6),("TIME",8),("SCORE",10)]
        hdr = tk.Frame(self.body, bg=P["dark2"])
        hdr.pack(fill="x", pady=(4,0))
        for h, w in cols:
            tk.Label(hdr, text=h, bg=P["dark2"], fg=P["pink"],
                     font=FNTB(9), width=w, anchor="w",
                     padx=8, pady=6).pack(side="left")

        cv = tk.Canvas(self.body, bg=P["bg"], highlightthickness=0)
        sb = tk.Scrollbar(self.body, orient="vertical", command=cv.yview)
        cv.configure(yscrollcommand=sb.set)
        cv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        inner = tk.Frame(cv, bg=P["bg"])
        cv.create_window((0,0), window=inner, anchor="nw")

        medals  = {0:"[1]", 1:"[2]", 2:"[3]"}
        rcols   = {0:P["yellow"], 1:P["muted"], 2:P["orange"]}
        for i, e in enumerate(entries):
            rbg = P["dark1"] if i%2==0 else P["panel"]
            row = tk.Frame(inner, bg=rbg)
            row.pack(fill="x")
            rc   = rcols.get(i, P["muted"])
            vals = [medals.get(i, f" {i+1} "), e["name"],
                    str(e["disks"]), str(e["moves"]),
                    f"{e['time']}s", f"{e['score']:,}"]
            fgs  = [rc, P["text"], P["text"], P["text"], P["accent"], P["green"]]
            for (_, w2), v, fg in zip(cols, vals, fgs):
                tk.Label(row, text=v, bg=rbg, fg=fg,
                         font=FNTB(10), width=w2, anchor="w",
                         padx=8, pady=8).pack(side="left")

        inner.update_idletasks()
        cv.configure(scrollregion=cv.bbox("all"))


# ═══════════════════════════════════════════════════════════
#  NETWORKING
# ═══════════════════════════════════════════════════════════
def get_all_local_ips():
    """Return every non-loopback IPv4 address on this machine."""
    ips = []
    try:
        # connect to external address (doesn't actually send data)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        s.connect(("8.8.8.8", 80))
        ips.append(s.getsockname()[0])
        s.close()
    except Exception:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None):
            if info[0] == socket.AF_INET:
                ip = info[4][0]
                if not ip.startswith("127.") and ip not in ips:
                    ips.append(ip)
    except Exception:
        pass
    if not ips:
        ips = ["127.0.0.1"]
    return ips


class NetServer:
    def __init__(self, port):
        self.on_move_cb  = None
        self.on_connect  = None   # called when client connects
        self.on_error    = None   # called on bind error
        self.conn        = None
        self.port        = port
        self.ips         = get_all_local_ips()
        self._srv        = None
        self._start()

    def _start(self):
        try:
            self._srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._srv.bind(("", self.port))
            self._srv.listen(1)
            threading.Thread(target=self._accept, daemon=True).start()
        except Exception as e:
            if self.on_error:
                self.on_error(str(e))

    def _accept(self):
        try:
            self._srv.settimeout(120)   # 2-minute wait
            self.conn, addr = self._srv.accept()
            self.conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            if self.on_connect:
                self.on_connect(addr[0])
            threading.Thread(target=self._recv, daemon=True).start()
        except socket.timeout:
            if self.on_error:
                self.on_error("Timed out waiting for opponent (2 min)")
        except Exception as e:
            if self.on_error:
                self.on_error(str(e))

    def _recv(self):
        buf = ""
        while True:
            try:
                d = self.conn.recv(4096).decode("utf-8", errors="ignore")
                if not d:
                    break
                buf += d
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        if self.on_move_cb:
                            self.on_move_cb(obj)
                    except json.JSONDecodeError:
                        pass
            except Exception:
                break

    def send(self, obj):
        if self.conn:
            try:
                self.conn.sendall((json.dumps(obj) + "\n").encode())
            except Exception:
                pass

    def close(self):
        try:
            if self._srv:
                self._srv.close()
        except Exception:
            pass
        try:
            if self.conn:
                self.conn.close()
        except Exception:
            pass


class NetClient:
    def __init__(self, host_ip, port, timeout=8):
        self.on_move_cb = None
        self.on_error   = None
        self.sock       = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)
        self.sock.connect((host_ip, port))          # raises on failure
        self.sock.settimeout(None)                  # blocking after connect
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        threading.Thread(target=self._recv, daemon=True).start()

    def _recv(self):
        buf = ""
        while True:
            try:
                d = self.sock.recv(4096).decode("utf-8", errors="ignore")
                if not d:
                    break
                buf += d
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        if self.on_move_cb:
                            self.on_move_cb(obj)
                    except json.JSONDecodeError:
                        pass
            except Exception:
                break

    def send(self, obj):
        try:
            self.sock.sendall((json.dumps(obj) + "\n").encode())
        except Exception:
            pass

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass



# ═══════════════════════════════════════════════════════════
#  BOT AI  —  solves Tower of Hanoi optimally with delay
# ═══════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════
#  REAL BOT AI  —  search-based with genuine human-like cognition
# ═══════════════════════════════════════════════════════════
def _hanoi_optimal(n, src, dst, aux):
    """Generate optimal move list for n disks."""
    moves = []
    def _rec(n, s, d, a):
        if n == 0: return
        _rec(n-1, s, a, d)
        moves.append((s, d))
        _rec(n-1, a, d, s)
    _rec(n, src, dst, aux)
    return moves


class BotPersonality:
    """
    Defines a bot's cognitive profile:
      move_time_lo/hi  — base ms per move
      burst_lo/hi      — ms during "flow state" burst
      think_depth      — how many disks deep it can plan (>n = perfect)
      memory_decay     — chance per move it forgets its plan and re-derives
      blunder_rate     — chance of making a genuinely wrong move
      recover_pause    — ms it pauses after realising a mistake
      fatigue_rate     — extra ms added per move (tiredness)
      flow_threshold   — moves in a row before flow state kicks in
      frustration_rate — after N mistakes, speeds up recklessly
      confidence       — 0..1: how often it second-guesses valid moves
      startup_ms       — initial board-reading pause
    """
    __slots__ = [
        "move_time_lo","move_time_hi","burst_lo","burst_hi",
        "think_depth","memory_decay","blunder_rate","recover_pause",
        "fatigue_rate","flow_threshold","frustration_rate",
        "confidence","startup_ms","name","color"
    ]
    def __init__(self, **kw):
        for k,v in kw.items(): setattr(self, k, v)


BOT_PERSONALITIES = {
    "EASY": BotPersonality(
        name="EASY",       color="#00ff44",
        move_time_lo=1800, move_time_hi=3400,
        burst_lo=900,      burst_hi=1600,
        think_depth=2,      # can only plan 2 disks ahead — gets lost on larger stacks
        memory_decay=0.25,  # forgets plan 1-in-4 moves
        blunder_rate=0.22,  # makes genuinely wrong moves often
        recover_pause=2200, # long confused pause after mistake
        fatigue_rate=0.018, # gets tired quickly
        flow_threshold=999, # never reaches flow
        frustration_rate=2, # 2 mistakes = reckless
        confidence=0.45,    # second-guesses itself a lot
        startup_ms=2500,
    ),
    "MEDIUM": BotPersonality(
        name="MEDIUM",     color="#ffe600",
        move_time_lo=860,  move_time_hi=1700,
        burst_lo=380,      burst_hi=760,
        think_depth=4,      # plans 4 disks ahead
        memory_decay=0.10,
        blunder_rate=0.07,
        recover_pause=1200,
        fatigue_rate=0.007,
        flow_threshold=6,   # reaches flow after 6 clean moves
        frustration_rate=4,
        confidence=0.72,
        startup_ms=1400,
    ),
    "HARD": BotPersonality(
        name="HARD",       color="#ff7b00",
        move_time_lo=340,  move_time_hi=680,
        burst_lo=140,      burst_hi=300,
        think_depth=6,
        memory_decay=0.03,
        blunder_rate=0.015,
        recover_pause=600,
        fatigue_rate=0.002,
        flow_threshold=4,
        frustration_rate=6,
        confidence=0.90,
        startup_ms=800,
    ),
    "EXPERT": BotPersonality(
        name="EXPERT",     color="#ff1144",
        move_time_lo=500,  move_time_hi=860,   # ~40% slower than before
        burst_lo=230,      burst_hi=440,
        think_depth=99,     # essentially perfect planning
        memory_decay=0.005,
        blunder_rate=0.012,
        recover_pause=480,
        fatigue_rate=0.001,
        flow_threshold=3,
        frustration_rate=8,
        confidence=0.97,
        startup_ms=800,
    ),
}


class BotAI:
    """
    Search-based AI with genuine human-like cognition.

    Instead of following a pre-computed script, the bot:
      - Derives its plan by searching the current board state
      - Has a working memory limit (think_depth) — deeper sub-problems
        exceed its lookahead and it guesses, making real mistakes
      - Forgets its plan (memory_decay) and has to re-derive it mid-game
      - Enters "flow state" after consecutive clean moves (speeds up)
      - Gets "frustrated" after mistakes (speeds up recklessly)
      - Has "confidence" — low confidence = second-guessing valid moves
      - Recovers from its own mistakes by replanning from the new state
      - Accumulates fatigue over a long game
    """

    def __init__(self, state: HanoiState, difficulty: str = "MEDIUM"):
        self.state   = state
        self.persona = BOT_PERSONALITIES.get(difficulty, BOT_PERSONALITIES["MEDIUM"])
        self.difficulty = difficulty

        # callbacks
        self.on_move    = None
        self.on_done    = None
        self.on_think   = None
        self.on_lift    = None
        self.on_blunder = None
        self.on_illegal = None

        # runtime state
        self._running     = False
        self._paused      = False
        self._slow_factor = 1.0
        self._after       = None

        # cognitive state
        self._plan        = []    # current planned move sequence (src,dst)
        self._plan_depth  = 0    # how many disks this plan covers
        self._move_count  = 0    # total moves made
        self._clean_streak = 0   # consecutive correct moves (for flow)
        self._mistake_count = 0  # total mistakes (for frustration)
        self._in_flow     = False
        self._frustrated  = False
        self._confusion   = 0.0  # 0..1 accumulated confusion after mistakes

        self._replan()  # build initial plan

    # ── Planning ──────────────────────────────────────────────────────────────

    def _replan(self):
        """
        Derive a move plan from the CURRENT board state.
        Uses limited think_depth: if the sub-problem is deeper than
        think_depth, the bot may choose a plausible-but-wrong move.
        """
        pegs = self.state.pegs
        n    = self.state.n

        # Find where disks are and what the goal is
        # Goal: all disks on peg 2
        # Work out which sub-problem we're in
        top_unsolved = self._find_top_unsolved()

        if top_unsolved == 0:
            # Fully solved — shouldn't happen but handle gracefully
            self._plan = []
            return

        depth = top_unsolved   # how many disks involved in current sub-problem
        p     = self.persona

        if depth <= p.think_depth:
            # Within planning depth — generate correct optimal sub-plan
            src_peg  = self._find_disk_peg(top_unsolved)
            dst_peg  = 2
            aux_peg  = 3 - src_peg - dst_peg
            if aux_peg < 0: aux_peg = 1
            self._plan = _hanoi_optimal(depth, src_peg, dst_peg, aux_peg)
            self._plan_depth = depth
        else:
            # Beyond planning depth — bot can only see part of the solution
            # It generates a partial correct plan for think_depth disks
            # then will have to replan when that runs out
            visible_depth = p.think_depth
            src_peg  = self._find_disk_peg(top_unsolved)
            dst_peg  = 2
            aux_peg  = 3 - src_peg - dst_peg
            if aux_peg < 0: aux_peg = 1
            # Plan only for the top `visible_depth` disks
            partial = _hanoi_optimal(visible_depth, src_peg, aux_peg, dst_peg)
            self._plan = partial[:max(1, len(partial)//2)]  # even more limited
            self._plan_depth = visible_depth

    def _find_top_unsolved(self):
        """Return the largest disk not yet on peg 2."""
        n = self.state.n
        for disk in range(n, 0, -1):
            if not (self.state.pegs[2] and self.state.pegs[2][0] == n
                    and self.state.pegs[2].count(disk)):
                # Check if disk is already correctly placed at the bottom of peg 2
                peg2 = self.state.pegs[2]
                correct_bottom = list(range(n, n - len(peg2), -1))
                if peg2 != correct_bottom or len(peg2) < disk:
                    return disk
        return 0

    def _find_disk_peg(self, disk):
        """Return which peg contains the given disk."""
        for i, peg in enumerate(self.state.pegs):
            if disk in peg:
                return i
        return 0

    def _next_correct_move(self):
        """Get the next move from the plan, replanning if empty."""
        if not self._plan:
            self._replan()
        if self._plan:
            return self._plan.pop(0)
        return None

    def _random_legal_move(self):
        """Pick a random legal move (used when confused)."""
        moves = []
        for s in range(3):
            for d in range(3):
                if s != d:
                    ok, _ = self.state.can_move(s, d)
                    if ok:
                        moves.append((s, d))
        return random.choice(moves) if moves else None

    def _random_wrong_move(self):
        """
        Make a genuinely wrong move: move a disk to the wrong peg.
        Simulates the human error of losing track of the goal.
        """
        # Try to move the top disk to ANY peg that isn't optimal
        for src in range(3):
            if not self.state.pegs[src]: continue
            for dst in range(3):
                if dst == src: continue
                ok, _ = self.state.can_move(src, dst)
                if ok:
                    # Check if this is actually sub-optimal
                    # (could still be correct by luck; that's fine — it's human)
                    return src, dst
        return None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self, after_fn):
        self._after   = after_fn
        self._running = True
        self._timer_id = self._after(
            self.persona.startup_ms + random.randint(-200, 400),
            self._think_and_move)

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False
        self._schedule_next()

    def stop(self):
        self._running = False

    def slow_down(self, factor=1.8):
        self._slow_factor = factor
        self._after(6000, self._clear_slow)

    def _clear_slow(self):
        self._slow_factor = 1.0

    # ── Timing ────────────────────────────────────────────────────────────────

    def _move_delay(self, extra=0):
        p = self.persona

        # Base timing
        lo, hi = p.move_time_lo, p.move_time_hi

        # Flow state: after clean_streak moves, speed up
        if self._in_flow and self._clean_streak >= p.flow_threshold:
            lo, hi = p.burst_lo, p.burst_hi

        # Frustration: reckless speed after many mistakes
        if self._frustrated:
            lo, hi = int(lo * 0.55), int(hi * 0.55)

        # Fatigue: cumulative slowdown
        fatigue = int(self._move_count * p.fatigue_rate * 1000)

        # Confusion: slow down when uncertain
        confusion_ms = int(self._confusion * 800)

        delay = int((random.randint(lo, hi) + extra + fatigue + confusion_ms)
                    * self._slow_factor)
        return max(80, delay)

    def _schedule_next(self, extra=0):
        if not self._running or self._paused: return
        delay = self._move_delay(extra)
        self._timer_id = self._after(delay, self._think_and_move)

    # ── Core decision loop ────────────────────────────────────────────────────

    def _think_and_move(self):
        if not self._running: return
        if self.state.solved:
            if self.on_done: self.on_done()
            return

        p = self.persona

        # ── Memory decay: forget plan and re-derive ──────────────────────────
        if self._plan and random.random() < p.memory_decay:
            self._plan = []
            if self.on_think: self.on_think("BOT LOST ITS PLACE...")
            self._timer_id = self._after(
                random.randint(800, int(p.recover_pause * 0.7)),
                self._think_and_move)
            return

        # ── Confidence check: second-guess a valid move ───────────────────────
        if random.random() > p.confidence and self._plan:
            if self.on_think: self.on_think("BOT DOUBLE-CHECKS...")
            extra_pause = random.randint(400, 1400)
            self._confusion = min(1.0, self._confusion + 0.1)
            self._timer_id = self._after(extra_pause, self._think_and_move)
            return

        # ── Deep-think pause when plan runs out or at sub-problem boundary ───
        if not self._plan:
            thinks = random.choice([
                "BOT IS THINKING...", "BOT RECALCULATES...",
                "BOT STUDIES THE BOARD...", "BOT PLANS NEXT PHASE...",
                "BOT REASSESSES...",
            ])
            if self.on_think: self.on_think(thinks)
            think_ms = random.randint(
                int(p.recover_pause * 0.4),
                p.recover_pause)
            self._replan()
            self._timer_id = self._after(think_ms, self._think_and_move)
            return

        # ── Genuine blunder: make a wrong move ───────────────────────────────
        # Probability scales with confusion and difficulty
        effective_blunder = p.blunder_rate * (1.0 + self._confusion * 2.0)
        if random.random() < effective_blunder:
            wrong = self._random_wrong_move()
            if wrong:
                src, dst = wrong
                # Check it's not actually the same as the correct move
                correct = self._plan[0] if self._plan else None
                if correct and (src, dst) != correct:
                    if self.on_think: self.on_think("BOT MAKES A MISTAKE!")
                    if self.on_blunder: self.on_blunder()
                    self._execute_move(src, dst, is_mistake=True)
                    return

        # ── Normal move from plan ─────────────────────────────────────────────
        move = self._next_correct_move()
        if move is None:
            # No valid plan — pick randomly
            move = self._random_legal_move()
            if move is None:
                self._schedule_next()
                return

        src, dst = move
        if self.on_think: self.on_think("")
        self._execute_move(src, dst, is_mistake=False)

    def _execute_move(self, src, dst, is_mistake=False):
        """Execute src→dst, handle animation callbacks, schedule next."""
        if not self._running: return
        p = self.persona

        pegs_before = [list(pg) for pg in self.state.pegs]
        if self.on_lift: self.on_lift(src)

        ok, _ = self.state.do_move(src, dst)

        if ok:
            if self.on_move: self.on_move(src, dst, pegs_before)
            self._move_count += 1

            if is_mistake:
                # After a mistake, bot realises and has to replan
                self._clean_streak  = 0
                self._mistake_count += 1
                self._confusion      = min(1.0, self._confusion + 0.25)
                self._in_flow        = False
                self._plan           = []  # force replan from new (worse) state
                self._frustrated     = (self._mistake_count >=
                                        p.frustration_rate)
                # Long confused pause before replanning
                self._after(
                    random.randint(p.recover_pause,
                                   int(p.recover_pause * 1.8)),
                    self._replan_then_move)
            else:
                # Clean move — update flow/fatigue
                self._clean_streak += 1
                self._confusion     = max(0.0, self._confusion - 0.08)
                if self._clean_streak >= p.flow_threshold:
                    self._in_flow = True

                if self.state.solved:
                    if self.on_done: self.on_done()
                    return
                self._schedule_next()
        else:
            # Illegal move (locked/blocked) — not a plan mistake, external cause
            if self.on_illegal: self.on_illegal()
            self._plan = []   # replan around the new constraints
            self._schedule_next(extra=random.randint(200, 600))

    def _replan_then_move(self):
        """Called after a mistake: replan from current state then continue."""
        if not self._running: return
        if self.on_think: self.on_think("BOT CORRECTS ITSELF...")
        self._replan()
        self._confusion = max(0.0, self._confusion - 0.1)
        self._schedule_next()


# ═══════════════════════════════════════════════════════════
#  SCREEN: VS BOT SETUP
# ═══════════════════════════════════════════════════════════
class VsBotSetup(Screen):
    def __init__(self, master):
        super().__init__(master)
        self.dvar    = tk.IntVar(value=4)
        self.mvar    = tk.StringVar(value="classic")
        self.diffvar = tk.StringVar(value="MEDIUM")
        header_bar(self, "VS  BOT  SETUP", P["purple"],
                   master.go_menu).pack(fill="x")
        body = tk.Frame(self, bg=P["bg"])
        body.pack(expand=True)

        tk.Label(body, text="YOUR NAME", bg=P["bg"],
                 fg=P["muted"], font=FNTB(9)).pack(pady=(28,4))
        self.name_e = PixEntry(body, width=24, default="PLAYER1")
        self.name_e.pack(pady=2)

        tk.Label(body, text="NUMBER OF DISKS", bg=P["bg"],
                 fg=P["muted"], font=FNTB(9)).pack(pady=(18,4))
        disk_selector(body, self.dvar).pack()

        tk.Label(body, text="GAME MODE", bg=P["bg"],
                 fg=P["muted"], font=FNTB(9)).pack(pady=(18,4))
        mode_selector(body, self.mvar).pack()

        tk.Label(body, text="BOT DIFFICULTY", bg=P["bg"],
                 fg=P["muted"], font=FNTB(9)).pack(pady=(18,4))

        # Create info_lbl BEFORE _diff_row so select() can call _update_info safely
        self.info_lbl = tk.Label(body, text="", bg=P["dark1"],
                                  fg=P["purple"], font=FNTB(9),
                                  pady=6, padx=14, wraplength=420)

        self._diff_row(body)   # calls select("MEDIUM") -> _update_info() -> info_lbl.config()

        self.info_lbl.pack(pady=(10,4), fill="x", padx=40)

        tk.Frame(body, bg=P["border"], height=2).pack(fill="x", pady=18)
        PixBtn(body, "START BATTLE", P["purple"],
               self._start, w=240, h=54, font_size=13, icon="bolt").pack(pady=4)

    def _diff_row(self, parent):
        f = tk.Frame(parent, bg=P["bg"])
        f.pack()
        diffs = [
            ("EASY",   P["green"]),
            ("MEDIUM", P["yellow"]),
            ("HARD",   P["orange"]),
            ("EXPERT", P["red"]),
        ]
        self._diff_cvs = []
        DW, DH, B = 96, 42, 3

        def draw_diff(cv, label, col, hovered=False):
            cv.delete("all")
            sel = (label == self.diffvar.get())
            body = P["bg"] if sel else (P["dark2"] if hovered else P["panel"])
            cv.create_rectangle(0, 0, DW, DH, fill=col, outline="")
            cv.create_rectangle(B, B, DW-B, DH-B, fill=body, outline="")
            if sel:
                for xx in range(B, DW-B, 6):
                    cv.create_rectangle(xx, B, xx+2, B+2, fill=col, outline="")
            cv.create_rectangle(B, DH-B-2, DW-B, DH-B, fill=col, outline="")
            cv.create_text(DW//2, DH//2, text=label,
                           fill=P["white"] if sel else col, font=FNTB(10))

        def select(v):
            self.diffvar.set(v)
            self._update_info()
            for c2, lbl, col in self._diff_cvs:
                draw_diff(c2, lbl, col)

        for label, col in diffs:
            cv = tk.Canvas(f, width=DW, height=DH, bg=P["bg"],
                           highlightthickness=0, cursor="hand2")
            cv.pack(side="left", padx=4)
            draw_diff(cv, label, col)
            def _click(e, _l=label): select(_l)
            def _enter(e, _cv=cv, _l=label, _c=col):
                if _l != self.diffvar.get(): draw_diff(_cv, _l, _c, hovered=True)
            def _leave(e, _cv=cv, _l=label, _c=col):
                draw_diff(_cv, _l, _c)
            cv.bind("<Button-1>", _click)
            cv.bind("<Enter>",    _enter)
            cv.bind("<Leave>",    _leave)
            self._diff_cvs.append((cv, label, col))

        select("MEDIUM")

    def _update_info(self):
        info = {
            "EASY":   "EASY    — Plans only 2 disks ahead. Forgets often, blunders a lot, gets tired & frustrated quickly. Perfect for beginners.",
            "MEDIUM": "MEDIUM  — Plans 4 disks. Occasionally forgets its plan, makes real mistakes and has to recover. Fair challenge.",
            "HARD":   "HARD    — Plans 6 disks. Enters flow state, rarely blunders, but still gets confused on deep sub-problems.",
            "EXPERT": "EXPERT  — Near-perfect planning. Recovers fast from mistakes. Has flow bursts. Tough but human mistakes still happen.",
        }
        self.info_lbl.config(text=info.get(self.diffvar.get(), ""))

    def _get_name(self):
        return self.name_e.get().strip().upper() or "PLAYER1"

    def _start(self):
        n = self._get_name()
        self.master.start_vsbot(n, self.dvar.get(),
                                self.mvar.get(), self.diffvar.get())


# ═══════════════════════════════════════════════════════════
#  BLITZ GOLD + SHOP SYSTEM
# ═══════════════════════════════════════════════════════════
# Shop items: what gold buys
SHOP_ITEMS = [
    {"id":"freeze",   "name":"FREEZE",  "cost":3, "color":P["blue"],   "desc":"Freeze bot 5s"},
    {"id":"slowmo",   "name":"SLOW",    "cost":2, "color":P["accent"], "desc":"Slow bot 8s"},
    {"id":"unlock",   "name":"UNLOCK",  "cost":2, "color":P["green"],  "desc":"Free your disks"},
    {"id":"clear",    "name":"CLEAR",   "cost":2, "color":P["yellow"], "desc":"Clear blocked pegs"},
    {"id":"timewarp", "name":"WARP",    "cost":3, "color":P["purple"], "desc":"Freeze timer 6s"},
    {"id":"chaos_bot","name":"CHAOS",   "cost":4, "color":P["pink"],   "desc":"Lock bot disk 4s"},
    {"id":"double",   "name":"DOUBLE",  "cost":5, "color":P["orange"], "desc":"Next powerup x2 effect!"},
]

# Map shop item id to POWERUPS entry (or custom)
def _pu_for_id(pid):
    for p in POWERUPS:
        if p["id"] == pid:
            return p
    # custom items not in POWERUPS
    return {"id": pid, "name": pid.upper(), "label": pid.upper(),
            "desc": "", "color": P["orange"], "rarity": 1}


class GoldBar(tk.Canvas):
    """Animated gold coin counter shown in BLITZ mode."""
    W, H = 160, 34

    def __init__(self, parent, initial=0):
        super().__init__(parent, width=self.W, height=self.H,
                         bg=P["bg"], highlightthickness=0)
        self._gold    = initial
        self._anim    = 0.0
        self._flash   = 0      # frames to flash yellow
        self._delta   = 0      # +N shown briefly
        self.after(30, self._tick)
        self._draw()

    @property
    def gold(self): return self._gold

    def add(self, amount):
        self._gold  += amount
        self._flash  = 18
        self._delta  = amount
        self._draw()

    def spend(self, amount):
        if self._gold >= amount:
            self._gold -= amount
            self._draw()
            return True
        return False

    def _tick(self):
        self._anim = (self._anim + 0.15) % (2 * math.pi)
        if self._flash > 0:
            self._flash -= 1
        self._draw()
        self.after(30, self._tick)

    def _draw(self):
        self.delete("all")
        W, H = self.W, self.H
        # background pill
        self.create_rectangle(0, 0, W, H, fill=P["panel"], outline="")
        self.create_rectangle(0, 0, W, 2, fill=P["yellow"], outline="")

        # spinning pixel coin — 8×8 pixel block grid, squish-animated
        t     = self._anim
        cx2, cy2 = 18, H//2
        flash_col = P["yellow"] if self._flash > 0 else P["orange"]
        squeeze   = max(0.15, abs(math.cos(t)))
        g = 2   # block size
        # coin shape as pixel rows (7 rows, varying widths)
        coin_rows = [2,3,3,3,3,3,2]
        for ri, rw in enumerate(coin_rows):
            draw_w = max(1, int(rw * squeeze))
            for ci in range(draw_w):
                bx = cx2 + (ci - draw_w//2) * g
                by = cy2 + (ri - len(coin_rows)//2) * g
                shade = P["white"] if (ri==0 and ci==0) else flash_col
                self.create_rectangle(bx, by, bx+g, by+g, fill=shade, outline="")

        # gold amount
        col = P["yellow"] if self._flash > 0 else P["text"]
        self.create_text(36, H//2, text=f"{self._gold} GOLD",
                         fill=col, font=FNTB(10), anchor="w")

        # +N flash
        if self._flash > 0 and self._delta:
            alpha = self._flash / 18.0
            fcol  = P["yellow"] if alpha > 0.5 else P["orange"]
            self.create_text(W - 8, H//2, text=f"+{self._delta}",
                             fill=fcol, font=FNTB(9), anchor="e")


class ShopPanel(tk.Frame):
    """Slide-in shop: shows buyable powerups, deducts gold on purchase."""

    def __init__(self, parent, gold_bar, pu_bar, on_buy_cb):
        super().__init__(parent, bg=P["dark1"], bd=0)
        self._gold = gold_bar
        self._pu   = pu_bar
        self._cb   = on_buy_cb
        self._visible = False
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg=P["dark2"])
        hdr.pack(fill="x")
        tk.Label(hdr, text=" [SHOP]  SPEND GOLD ON POWERUPS ",
                 bg=P["dark2"], fg=P["yellow"], font=FNTB(9),
                 pady=4).pack(side="left")
        tk.Button(hdr, text="X", font=FNTB(9),
                  bg=P["dark2"], fg=P["red"], relief="flat",
                  cursor="hand2", command=self.hide).pack(side="right", padx=6)

        grid = tk.Frame(self, bg=P["dark1"])
        grid.pack(fill="x", padx=6, pady=4)

        for i, item in enumerate(SHOP_ITEMS):
            col  = item["color"]
            cost = item["cost"]
            f = tk.Canvas(grid, width=130, height=64,
                          bg=P["panel"], highlightthickness=1,
                          highlightbackground=col,
                          cursor="hand2")
            f.grid(row=i//4, column=i%4, padx=3, pady=3)

            def _draw_card(cv, item=item):
                cv.delete("all")
                c   = item["color"]
                cv.create_rectangle(0, 0, 130, 8, fill=c, outline="")
                draw_icon(cv, item["id"], 18, 36, size=26, color=c)
                cv.create_line(38, 10, 38, 58, fill=P["border"])
                cv.create_text(84, 22, text=item["name"],
                               fill=c, font=FNTB(9), anchor="center")
                cv.create_text(84, 38, text=item["desc"],
                               fill=P["muted"], font=FNT(7),
                               anchor="center", width=80)
                # cost badge
                cv.create_rectangle(96, 48, 126, 62,
                                    fill=P["yellow"], outline="")
                cv.create_text(111, 55, text=f"{item['cost']} G",
                               fill=P["bg"], font=FNTB(8), anchor="center")
            _draw_card(f)

            def _on_click(e, item=item, cv=f, draw=_draw_card):
                if self._gold.spend(item["cost"]):
                    pu = _pu_for_id(item["id"])
                    added = self._pu.add(pu)
                    if not added:
                        # inventory full — refund
                        self._gold.add(item["cost"])
                        return
                    if self._cb:
                        self._cb(item)
                    # flash green
                    cv.configure(highlightbackground=P["green"])
                    cv.after(500, lambda: cv.configure(
                        highlightbackground=item["color"]))
                else:
                    # flash red — not enough gold
                    cv.configure(highlightbackground=P["red"])
                    cv.after(500, lambda: cv.configure(
                        highlightbackground=item["color"]))
            f.bind("<Button-1>", _on_click)

        tk.Label(self, text="BOT BLUNDERS  = +1 GOLD  |  BOT ILLEGAL ATTEMPT = +2 GOLD  |  HOLD 3 POWERUPS MAX",
                 bg=P["dark1"], fg=P["border"], font=FNT(7), pady=3).pack()

    def show(self):
        if self._visible: return
        self._visible = True
        self._anim_progress = 0.0
        self.pack(fill="x", padx=8, pady=2)
        self.configure(height=1)
        self._slide_in()

    def hide(self):
        if not self._visible: return
        self._visible = False
        self._slide_out()

    def toggle(self):
        if self._visible: self.hide()
        else: self.show()

    def _slide_in(self):
        """Animate height from 0 to full over ~180ms."""
        self._anim_progress = min(1.0, self._anim_progress + 0.12)
        t = self._anim_progress
        # ease-out cubic
        t_ease = 1 - (1 - t) ** 3
        target_h = 140   # approximate full shop height
        h = max(2, int(target_h * t_ease))
        try:
            self.configure(height=h)
            # draw a scan-line sweep effect on the header during open
            self._scan_t = getattr(self, "_scan_t", 0) + 1
        except Exception:
            pass
        if self._anim_progress < 1.0:
            self.after(16, self._slide_in)
        else:
            self.configure(height=0)   # let pack geometry manage height
            self._draw_open_flash()

    def _slide_out(self):
        """Animate height from full to 0, then pack_forget."""
        self._anim_out = getattr(self, "_anim_out", 0) + 0.15
        t = min(1.0, self._anim_out)
        t_ease = t * t   # ease-in
        target_h = 140
        h = max(1, int(target_h * (1.0 - t_ease)))
        try:
            self.configure(height=h)
        except Exception:
            pass
        if t < 1.0:
            self.after(16, self._slide_out)
        else:
            self._anim_out = 0
            self.pack_forget()

    def _draw_open_flash(self):
        """Brief color flash on all item cards when shop fully opens."""
        for widget in self.winfo_children():
            if isinstance(widget, tk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, tk.Canvas):
                        orig = child.cget("highlightbackground")
                        child.configure(highlightbackground=P["yellow"])
                        child.after(220, lambda c=child, o=orig:
                                    c.configure(highlightbackground=o)
                                    if c.winfo_exists() else None)


# ═══════════════════════════════════════════════════════════
#  SCREEN: VS BOT GAME  (with BLITZ powerup mode)
# ═══════════════════════════════════════════════════════════
# POWERUP definitions for BLITZ mode
POWERUPS = [
    {
        "id":     "freeze",
        "name":   "FREEZE",
        "label":  "BOT FREEZE",
        "desc":   "Bot pauses for 5 seconds!",
        "color":  P["blue"],
        "rarity": 3,
    },
    {
        "id":     "slowmo",
        "name":   "SLOW",
        "label":  "SLOW BOT",
        "desc":   "Bot moves 2x slower for 8s!",
        "color":  P["accent"],
        "rarity": 3,
    },
    {
        "id":     "unlock",
        "name":   "UNLOCK",
        "label":  "UNLOCK ALL",
        "desc":   "All your locked disks freed!",
        "color":  P["green"],
        "rarity": 2,
    },
    {
        "id":     "clear",
        "name":   "CLEAR",
        "label":  "CLR BLOCKS",
        "desc":   "All blocked pegs cleared!",
        "color":  P["yellow"],
        "rarity": 2,
    },
    {
        "id":     "timewarp",
        "name":   "WARP",
        "label":  "TIME WARP",
        "desc":   "Your timer freezes 6s!",
        "color":  P["purple"],
        "rarity": 2,
    },
    {
        "id":     "chaos_bot",
        "name":   "CHAOS",
        "label":  "BOT CHAOS",
        "desc":   "Locks a random bot disk 4s!",
        "color":  P["pink"],
        "rarity": 1,
    },
]

class PowerupCard(tk.Canvas):
    """Single clickable powerup card with pixel-art canvas icon."""
    CARD_W = 110
    CARD_H = 56

    def __init__(self, parent, pu, on_use_cb, idx):
        super().__init__(parent, width=self.CARD_W, height=self.CARD_H,
                         bg=P["bg"], highlightthickness=0, cursor="hand2")
        self._pu     = pu
        self._on_use = on_use_cb
        self._idx    = idx
        self._hover  = False
        self.bind("<Enter>",         self._enter)
        self.bind("<Leave>",         self._leave)
        self.bind("<Button-1>",      self._click)
        self._draw()

    def _draw(self):
        self.delete("all")
        w, h   = self.CARD_W, self.CARD_H
        col    = self._pu["color"]
        bg_col = P["dark2"] if self._hover else P["panel"]

        # card border (2px glow when hovered)
        bw = 3 if self._hover else 2
        self.create_rectangle(0, 0, w, h, fill=P["bg"], outline="")
        self.create_rectangle(2, 2, w-2, h-2, fill=bg_col, outline=col, width=bw)
        # top accent bar
        self.create_rectangle(2, 2, w-2, 7, fill=col, outline="")

        # pixel icon (left side, centred vertically)
        icon_id = self._pu.get("id", "bolt")
        draw_icon(self, icon_id, 22, h//2+4, size=26, color=col)

        # vertical separator
        self.create_line(44, 10, 44, h-8, fill=col, width=1)

        # name text (right side)
        name = self._pu.get("name", self._pu.get("label","?"))
        self.create_text(w//2+20, h//2, text=name,
                         fill=P["white"] if self._hover else col,
                         font=FNTB(8), anchor="center",
                         width=w-50)

    def _enter(self, e): self._hover=True;  self._draw()
    def _leave(self, e): self._hover=False; self._draw()
    def _click(self, e): self._on_use(self._idx)


class PowerupBar(tk.Frame):
    """Holds up to 3 collected powerups as clickable pixel cards with canvas icons."""
    def __init__(self, parent, on_use_cb):
        super().__init__(parent, bg=P["bg"])
        self._slots   = []
        self._on_use  = on_use_cb
        # label
        lbl_cv = tk.Canvas(self, width=90, height=56,
                            bg=P["bg"], highlightthickness=0)
        lbl_cv.pack(side="left", padx=(6,2))
        lbl_cv.create_text(45, 20, text="POWER", fill=P["muted"], font=FNTB(8), anchor="center")
        lbl_cv.create_text(45, 34, text="UPS",   fill=P["muted"], font=FNTB(8), anchor="center")
        # draw bolt icon as label decoration
        draw_icon(lbl_cv, "bolt", 45, 48, size=12, color=P["pink"])
        self._slot_frame = tk.Frame(self, bg=P["bg"])
        self._slot_frame.pack(side="left")
        self._refresh()

    def add(self, pu):
        if len(self._slots) < 3:
            self._slots.append(pu)
            self._refresh()
            return True
        return False

    def _refresh(self):
        for w in self._slot_frame.winfo_children():
            w.destroy()
        for i, pu in enumerate(self._slots):
            card = PowerupCard(self._slot_frame, pu, self._use, i)
            card.pack(side="left", padx=4, pady=2)
        # empty slot placeholders
        for _ in range(3 - len(self._slots)):
            self._empty_slot()

    def _empty_slot(self):
        cv = tk.Canvas(self._slot_frame,
                       width=PowerupCard.CARD_W,
                       height=PowerupCard.CARD_H,
                       bg=P["bg"], highlightthickness=0)
        cv.pack(side="left", padx=4, pady=2)
        w, h = PowerupCard.CARD_W, PowerupCard.CARD_H
        # dashed border
        for x in range(2, w-2, 8):
            cv.create_rectangle(x, 2, x+4, 4, fill=P["border"], outline="")
            cv.create_rectangle(x, h-4, x+4, h-2, fill=P["border"], outline="")
        for y in range(2, h-2, 8):
            cv.create_rectangle(2, y, 4, y+4, fill=P["border"], outline="")
            cv.create_rectangle(w-4, y, w-2, y+4, fill=P["border"], outline="")
        cv.create_text(w//2, h//2, text="EMPTY",
                       fill=P["border"], font=FNTB(8), anchor="center")

    def _use(self, idx):
        if idx < len(self._slots):
            pu = self._slots.pop(idx)
            self._refresh()
            self._on_use(pu)


class VsBotGame(Screen):
    def __init__(self, master, name, disks, mode, difficulty):
        super().__init__(master)
        self.name       = name
        self.disks      = disks
        self.mode       = mode
        self.difficulty = difficulty

        self.p_state  = HanoiState(disks)
        self.b_state  = HanoiState(disks)

        self.p_t0 = None
        self.b_t0 = time.time()
        self.p_t1 = self.b_t1 = None
        self._p_time_frozen = False   # BLITZ timewarp powerup

        self._tid  = None
        self._cid  = None
        self._puid = None   # powerup spawn timer

        self._gold_amount = 0   # gold earned this game (blitz) -- 3 starter gold

        self.bot = BotAI(self.b_state, difficulty)
        self.bot.on_move    = self._bot_moved
        self.bot.on_done    = self._bot_done
        self.bot.on_think   = self._bot_think
        self.bot.on_lift    = self._bot_lift
        self.bot.on_blunder = self._bot_blundered
        self.bot.on_illegal = self._bot_illegal

        self._build()
        self.bot.start(self.after)
        if mode in ("chaos", "blitz"):
            self._sched_chaos()
        if mode == "blitz":
            self._sched_powerup()

    def _build(self):
        diff_col = {"EASY":P["green"],"MEDIUM":P["yellow"],
                    "HARD":P["orange"],"EXPERT":P["red"]}.get(self.difficulty, P["purple"])
        mode_col = {"classic":P["accent"],"chaos":P["orange"],"blitz":P["pink"]}.get(self.mode, P["accent"])

        self.hud = HudBar(self, [self.name, f"BOT [{self.difficulty}]"],
                          self.mode, self._quit, self._restart)
        self.hud.pack(fill="x")

        # Info strip
        strip = tk.Frame(self, bg=P["bg"])
        strip.pack(fill="x", padx=8, pady=2)
        tk.Label(strip, text=f"  MODE: {self.mode.upper()}  ",
                 bg=mode_col, fg=P["bg"], font=FNTB(9)).pack(side="left", padx=4)
        tk.Label(strip, text=f"  BOT: {self.difficulty}  ",
                 bg=diff_col, fg=P["bg"], font=FNTB(9)).pack(side="left", padx=4)

        # Bot thinking label
        self.think_lbl = tk.Label(strip, text="",
                                   bg=P["bg"], fg=P["purple"], font=FNTB(9))
        self.think_lbl.pack(side="right", padx=8)

        # Powerup bar + gold + shop (blitz only)
        if self.mode == "blitz":
            blitz_row = tk.Frame(self, bg=P["bg"])
            blitz_row.pack(fill="x", padx=8, pady=2)

            self.pu_bar  = PowerupBar(blitz_row, self._use_powerup)
            self.pu_bar.pack(side="left", fill="x", expand=True)

            self.gold_bar = GoldBar(blitz_row, initial=3)
            self.gold_bar.pack(side="left", padx=8)

            # SHOP toggle button (canvas drawn)
            shop_btn = tk.Canvas(blitz_row, width=72, height=34,
                                 bg=P["bg"], highlightthickness=0, cursor="hand2")
            shop_btn.pack(side="left", padx=4)
            def _draw_shop(h=False):
                shop_btn.delete("all")
                c = P["yellow"] if h else P["orange"]
                shop_btn.create_rectangle(1,1,71,33, outline=c, fill=P["panel"], width=2)
                draw_icon(shop_btn, "crown", 16, 17, size=18, color=c)
                shop_btn.create_text(44, 17, text="SHOP",
                                     fill=c, font=FNTB(8), anchor="center")
            _draw_shop(False)
            shop_btn.bind("<Enter>",    lambda e: _draw_shop(True))
            shop_btn.bind("<Leave>",    lambda e: _draw_shop(False))
            shop_btn.bind("<Button-1>", lambda e: self.shop.toggle())

            # Shop panel (hidden by default, below blitz row)
            self.shop = ShopPanel(self, self.gold_bar, self.pu_bar,
                                  self._on_shop_buy)

            # Spawn notification label
            self.pu_msg = tk.Label(self, text="",
                                    bg=P["panel"], fg=P["pink"],
                                    font=FNTB(10), pady=4)
            self.pu_msg.pack(fill="x")

        # Message bar
        self.msg = tk.Label(self, text="RACE THE BOT!  SOLVE YOUR BOARD FIRST!",
                            bg=P["bg2"], fg=P["muted"], font=FNTB(10), pady=5)
        self.msg.pack(fill="x")

        # Boards
        boards = tk.Frame(self, bg=P["bg"])
        boards.pack(fill="both", expand=True, padx=8, pady=4)

        self.p_board = BoardCanvas(boards, self.p_state,
                                    interactive=True,
                                    label=f"YOU  —  {self.name}")
        self.p_board.pack(side="left", fill="both", expand=True, padx=(0,4))
        self.p_board.on_move = self._player_moved

        self.b_board = BoardCanvas(boards, self.b_state,
                                    interactive=False,
                                    label=f"BOT  [{self.difficulty}]")
        self.b_board.pack(side="right", fill="both", expand=True, padx=(4,0))
        self.b_board.configure(highlightbackground=P["purple"])

        mode_hints = {
            "classic": "CLASSIC  |  A/S/D = PEG A/B/C  |  ESC = DESELECT",
            "chaos":   "CHAOS  |  A/S/D = PEG A/B/C  |  SURVIVE THE RANDOM EVENTS!",
            "blitz":   "BLITZ  |  A/S/D = PEGS  |  1/2/3 = USE POWERUP SLOT",
        }
        tk.Label(self, text=mode_hints.get(self.mode,""),
                 bg=P["bg"], fg=P["border"], font=FNT(8)).pack(pady=(0,3))

        self._bind_keys(self.p_board)
        self._tid = self.after(100, self._tick)

    def _bind_keys(self, board):
        def _key(e):
            k = e.keysym.lower()
            if   k in ("a","q"):   board.key_press(0)
            elif k in ("s","w"):   board.key_press(1)
            elif k in ("d","e"):   board.key_press(2)
            elif k == "escape":    board.selected = None
            # BLITZ: 1/2/3 use powerup slots
            elif k == "1" and self.mode == "blitz" and len(self.pu_bar._slots) >= 1:
                self.pu_bar._use(0)
            elif k == "2" and self.mode == "blitz" and len(self.pu_bar._slots) >= 2:
                self.pu_bar._use(1)
            elif k == "3" and self.mode == "blitz" and len(self.pu_bar._slots) >= 3:
                self.pu_bar._use(2)
        self.master.bind("<Key>", _key)
        self.master.focus_set()

    # ── player ────────────────────────────────────────────
    def _player_moved(self, src, dst, ok, msg):
        if src == -1:
            self.msg.config(text=f"! {msg}", fg=P["red"]); return
        if ok:
            if self.p_t0 is None: self.p_t0 = time.time()
            self.msg.config(
                text=f"YOU: {['A','B','C'][src]} >> {['A','B','C'][dst]}",
                fg=P["green"])
            if self.p_state.solved:
                self.p_t1 = time.time()
                self._check_result()
        else:
            self.msg.config(text=f"! {msg}", fg=P["red"])

    # ── bot callbacks ─────────────────────────────────────
    def _bot_moved(self, src, dst, pegs_before):
        if self.b_t0 is None: self.b_t0 = time.time()
        # clear ghost now that move is complete
        self.b_board.op_selected = None
        # trigger fly animation on the bot board
        if self.b_state.pegs[dst]:
            disk = self.b_state.pegs[dst][-1]
            self.b_board._launch_fly(disk, src, dst, pegs_before)
        # particle burst at destination
        W2  = max(self.b_board.winfo_width(), 460)
        H2  = max(self.b_board.winfo_height(), 400)
        PAD = 32; cW = (W2-PAD*2)/3
        px  = PAD + cW*(dst+0.5)
        by  = H2-68
        dh  = max(14, min(30, (int((H2-100)*0.78)-16)//(self.b_state.n+2)))
        py  = by - len(self.b_state.pegs[dst])*(dh+2)
        col = DISK_PAL[(self.b_state.pegs[dst][-1]-1) % len(DISK_PAL)][0] if self.b_state.pegs[dst] else P["purple"]
        self.b_board.parts.burst(px, py, col, n=10, speed=3.0)

    def _bot_done(self):
        self.b_t1 = time.time()
        self._check_result()

    def _bot_think(self, msg):
        self.think_lbl.config(text=msg)

    def _bot_lift(self, src_peg):
        """Show ghost on bot board when it picks up a disk."""
        self.b_board.op_selected = src_peg

    def _bot_blundered(self):
        """Bot made a mistake — award gold in BLITZ mode."""
        if self.mode != "blitz": return
        self.gold_bar.add(1)
        self.msg.config(text="[!] BOT BLUNDERED!  +1 GOLD EARNED!", fg=P["yellow"])
        W2 = max(self.b_board.winfo_width(), 460)
        H2 = max(self.b_board.winfo_height(), 400)
        self.b_board.parts.burst(W2//2, H2//2, P["yellow"], n=20, speed=4.0)

    def _bot_illegal(self):
        """Bot hit an illegal move (e.g. locked disk) — award +2 gold."""
        if self.mode != "blitz": return
        self.gold_bar.add(2)
        self.msg.config(text="[!] BOT HIT LOCKED DISK!  +2 GOLD!", fg=P["yellow"])
        W2 = max(self.b_board.winfo_width(), 460)
        H2 = max(self.b_board.winfo_height(), 400)
        self.b_board.parts.burst(W2//2, H2//2, P["orange"], n=30, speed=5.0)

    def _on_shop_buy(self, item):
        """Called after a successful shop purchase."""
        self.msg.config(
            text=f"[>] BOUGHT: {item['name']}  ({item['cost']} GOLD SPENT)",
            fg=item["color"])

    # ── result ────────────────────────────────────────────
    def _check_result(self):
        p_done = self.p_state.solved
        b_done = self.b_state.solved
        if p_done and b_done:
            pt = (self.p_t1 or time.time()) - (self.p_t0 or self.b_t0)
            bt = (self.b_t1 or time.time()) - self.b_t0
            pm = self.p_state.moves
            bm = self.b_state.moves
            if pm < bm:
                result, col = "YOU WIN!  FEWER MOVES!", P["yellow"]
            elif pm == bm and pt < bt:
                result, col = "YOU WIN!  FASTER TIME!", P["yellow"]
            elif pm == bm and pt == bt:
                result, col = "DRAW!", P["accent"]
            else:
                result, col = f"BOT WINS! ({self.difficulty})", P["red"]
            self.msg.config(
                text=f"{result}   YOU:{pm}mv {pt:.1f}s   BOT:{bm}mv {bt:.1f}s", fg=col)
            if self.p_t0:
                self.master.scores.add(self.mode, self.name, self.disks, pm, pt)
        elif p_done:
            self.msg.config(text="YOU SOLVED IT!  BOT IS STILL GOING...", fg=P["yellow"])
        elif b_done:
            self.msg.config(text="BOT FINISHED!  YOU CAN STILL WIN WITH FEWER MOVES!", fg=P["orange"])

    # ── CHAOS events ──────────────────────────────────────
    def _sched_chaos(self):
        self._cid = self.after(random.randint(9000,18000), self._chaos)

    def _chaos(self):
        if self.p_state.solved: return
        s  = self.p_state
        ev = random.choice(["lock","lock","block","unlock"])
        if ev == "lock":
            all_d = [d for pg in s.pegs for d in pg]
            if all_d:
                disk = random.choice(all_d)
                s.locked.add(disk)
                self.msg.config(text=f"! CHAOS: DISK {disk} LOCKED 5s!", fg=P["orange"])
                self.after(5000, lambda d=disk: s.locked.discard(d))
        elif ev == "block":
            empty = [k for k in range(3) if not s.pegs[k]]
            if empty:
                peg = random.choice(empty)
                s.blocked.add(peg)
                self.msg.config(text=f"! CHAOS: PEG {['A','B','C'][peg]} BLOCKED 6s!", fg=P["red"])
                self.after(6000, lambda p=peg: s.blocked.discard(p))
        elif ev == "unlock":
            s.locked.clear(); s.blocked.clear()
            self.msg.config(text="OK CHAOS CLEARED!", fg=P["green"])
        self._sched_chaos()

    # ── BLITZ powerup spawning ────────────────────────────
    def _sched_powerup(self):
        delay = random.randint(6000, 14000)
        self._puid = self.after(delay, self._spawn_powerup)

    def _spawn_powerup(self):
        if self.p_state.solved and self.b_state.solved: return
        # Weighted random selection
        pool = []
        for pu in POWERUPS:
            pool.extend([pu] * pu["rarity"])
        pu = random.choice(pool)
        added = self.pu_bar.add(pu)
        if added:
            self.pu_msg.config(
                text=f"[!] POWERUP: {pu['label']}  {pu['desc']}",
                fg=pu["color"])
            self.p_board.parts.burst(
                max(self.p_board.winfo_width(),460)//2,
                max(self.p_board.winfo_height(),400)//2,
                pu["color"], n=30, speed=5.0)
            self.after(4000, lambda: self.pu_msg.config(text=""))
        self._sched_powerup()

    def _use_powerup(self, pu):
        pid = pu["id"]
        col = pu["color"]
        W   = max(self.b_board.winfo_width(), 460)
        H   = max(self.b_board.winfo_height(), 400)

        if pid == "freeze":
            self.bot.pause()
            self.think_lbl.config(text="BOT FROZEN!")
            self.b_board.configure(highlightbackground=P["blue"])
            self.b_board.parts.burst(W//2, H//2, P["blue"], n=40, speed=4.0)
            self.msg.config(text="[*] BOT FROZEN FOR 5 SECONDS!", fg=P["blue"])
            def unfreeze():
                self.bot.resume()
                self.think_lbl.config(text="")
                self.b_board.configure(highlightbackground=P["purple"])
            self.after(5000, unfreeze)

        elif pid == "slowmo":
            self.bot.slow_down(factor=2.2)
            self.b_board.parts.burst(W//2, H//2, P["accent"], n=30, speed=3.0)
            self.msg.config(text="[~] BOT SLOWED DOWN FOR 8 SECONDS!", fg=P["accent"])

        elif pid == "unlock":
            self.p_state.locked.clear()
            self.p_board.parts.burst(
                max(self.p_board.winfo_width(),460)//2,
                max(self.p_board.winfo_height(),400)//2,
                P["green"], n=35, speed=4.5)
            self.msg.config(text="[O] ALL YOUR DISKS UNLOCKED!", fg=P["green"])

        elif pid == "clear":
            self.p_state.blocked.clear()
            self.msg.config(text="[+] ALL YOUR BLOCKED PEGS CLEARED!", fg=P["yellow"])

        elif pid == "timewarp":
            self._p_time_frozen = True
            self._frozen_at = time.time()
            self.msg.config(text="[>] YOUR TIMER FROZEN FOR 6 SECONDS!", fg=P["purple"])
            def unfreeze_time():
                if self.p_t0 and self._p_time_frozen:
                    frozen_duration = time.time() - self._frozen_at
                    self.p_t0 += frozen_duration   # shift start forward
                self._p_time_frozen = False
            self.after(6000, unfreeze_time)

        elif pid == "chaos_bot":
            all_d = [d for pg in self.b_state.pegs for d in pg]
            if all_d:
                disk = random.choice(all_d)
                self.b_state.locked.add(disk)
                self.b_board.parts.burst(W//2, H//2, P["pink"], n=40, speed=5.0)
                self.msg.config(text=f"[X] BOT DISK {disk} LOCKED FOR 4 SECONDS!", fg=P["pink"])
                self.after(4000, lambda d=disk: self.b_state.locked.discard(d))

        # Visual flash on used board
        if pid in ("freeze","slowmo","chaos_bot"):
            self.b_board._bad()
        else:
            self.p_board._flash_col = col
            self.p_board._flash_t   = 8

    # ── tick ──────────────────────────────────────────────
    def _tick(self):
        pt = (time.time()-self.p_t0) if (self.p_t0 and not self.p_state.solved
                                          and not self._p_time_frozen) else None
        bt = (time.time()-self.b_t0) if self.b_t0 and not self.b_state.solved else None
        self.hud.update_stats(self.name,               self.p_state.moves, pt)
        self.hud.update_stats(f"BOT [{self.difficulty}]", self.b_state.moves, bt)
        self._tid = self.after(100, self._tick)

    def _quit(self):
        self.on_destroy(); self.master.go_menu()

    def _restart(self):
        self.on_destroy()
        self.master.start_vsbot(self.name, self.disks, self.mode, self.difficulty)

    def on_destroy(self):
        self.bot.stop()
        if self._tid:  self.after_cancel(self._tid)
        if self._cid:  self.after_cancel(self._cid)
        if self._puid: self.after_cancel(self._puid)


# ═══════════════════════════════════════════════════════════
#  APP CONTROLLER
# ═══════════════════════════════════════════════════════════
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TOWER OF HANOI  —  PIXEL EDITION")
        self.geometry("1100x740")
        self.minsize(860, 620)
        self.configure(bg=P["bg"])
        self.scores  = Scores()
        self._screen = None
        self.go_menu()

    def _set(self, s):
        if self._screen:
            try: self._screen.destroy()
            except Exception: pass
        self._screen = s
        s.pack(fill="both", expand=True)

    def go_menu(self):   self._set(MenuScreen(self))
    def go_solo(self):   self._set(SoloSetup(self))
    def go_mp(self):     self._set(MPSetup(self))
    def go_vsbot(self):  self._set(VsBotSetup(self))
    def go_scores(self): self._set(ScoreScreen(self))

    def start_solo(self, name, disks, mode):
        self._set(SoloGame(self, name, disks, mode))

    def start_vsbot(self, name, disks, mode, difficulty):
        self._set(VsBotGame(self, name, disks, mode, difficulty))

    def mp_host(self, name, disks, mode, status_lbl, port=NET_PORT):
        try:
            srv = NetServer(port)
        except Exception as e:
            if status_lbl:
                status_lbl.config(text=f"BIND FAILED: {e}", fg=P["red"])
            return

        ip_str = "  /  ".join(srv.ips)
        if status_lbl:
            status_lbl.config(
                text=f"WAITING ON PORT {port}   YOUR IP: {ip_str}",
                fg=P["yellow"])

        def on_connect(addr):
            # called from background thread — just log
            pass

        def on_error(msg):
            self.after(0, lambda: status_lbl.config(
                text=f"SERVER ERROR: {msg}", fg=P["red"]) if status_lbl else None)

        srv.on_connect = on_connect
        srv.on_error   = on_error

        def first(obj):
            if obj.get("t") == "name":
                opp = obj.get("n", "GUEST")
                # Send name + config so joiner auto-matches host settings
                srv.send({"t": "name", "n": name})
                srv.send({"t": "config", "disks": disks, "mode": mode})
                srv.on_move_cb = None
                self.after(0, lambda: self._launch_mp(
                    name, opp, disks, mode, srv, True))
        srv.on_move_cb = first

    def mp_join(self, name, ip, disks, mode, status_lbl, port=NET_PORT):
        """Non-blocking join — runs connect in a background thread."""
        def _do_join():
            try:
                cli = NetClient(ip, port, timeout=10)
                cli.send({"t": "name", "n": name})
                if status_lbl:
                    self.after(0, lambda: status_lbl.config(
                        text=f"CONNECTED TO {ip}:{port}  WAITING FOR HOST...",
                        fg=P["green"]))

                join_state = {"opp": None, "disks": disks, "mode": mode}

                def first(obj):
                    t = obj.get("t")
                    if t == "name":
                        join_state["opp"] = obj.get("n", "HOST")
                    elif t == "config":
                        join_state["disks"] = obj.get("disks", disks)
                        join_state["mode"]  = obj.get("mode",  mode)
                    # Launch only once we have both name and config
                    if join_state["opp"] is not None:
                        cli.on_move_cb = None
                        opp   = join_state["opp"]
                        ndisk = join_state["disks"]
                        nmode = join_state["mode"]
                        self.after(0, lambda: self._launch_mp(
                            name, opp, ndisk, nmode, cli, False))
                cli.on_move_cb = first

            except ConnectionRefusedError:
                self.after(0, lambda: status_lbl.config(
                    text=f"CONNECTION REFUSED  —  is the host running?  Check IP & port.",
                    fg=P["red"]) if status_lbl else None)
            except socket.timeout:
                self.after(0, lambda: status_lbl.config(
                    text=f"TIMED OUT connecting to {ip}:{port}  —  check IP & port.",
                    fg=P["red"]) if status_lbl else None)
            except OSError as e:
                self.after(0, lambda: status_lbl.config(
                    text=f"NETWORK ERROR: {e}",
                    fg=P["red"]) if status_lbl else None)
            except Exception as e:
                self.after(0, lambda: status_lbl.config(
                    text=f"FAILED: {e}",
                    fg=P["red"]) if status_lbl else None)

        threading.Thread(target=_do_join, daemon=True).start()

    def _launch_mp(self, my_name, opp, disks, mode, net, is_host):
        screen = MPGame(self, my_name, opp, disks, mode, net, is_host)
        net.on_move_cb = screen._net_in
        self._set(screen)


# ═══════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = App()
    app.mainloop()