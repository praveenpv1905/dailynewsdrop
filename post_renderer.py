"""
post_renderer.py — DailyNewsDrop post template
1080x1080 Instagram-style post.
- With image: big text over dark overlay
- Without image: fills entire frame with extra-large text + decorative elements, NO empty space
"""
import re, base64
from pathlib import Path
from config import POSTS_DIR, BRAND_HANDLE, ACCENT_COLOR

# Pre-load logo once at module import time
_LOGO_PATH = Path(__file__).resolve().parent / "dnd_logo.png"
_LOGO_B64  = ""
if _LOGO_PATH.exists():
    _LOGO_B64 = "data:image/png;base64," + base64.b64encode(_LOGO_PATH.read_bytes()).decode()


def _colorize(text: str, keywords: list, accent: str) -> str:
    if not keywords:
        return text
    kws     = sorted(set(keywords), key=len, reverse=True)
    pattern = "(" + "|".join(re.escape(k) for k in kws) + ")"
    return re.sub(pattern, f'<span class="hi">\\1</span>', text, flags=re.IGNORECASE)


def _font_size(char_count: int, has_image: bool) -> str:
    """Pick headline font size. No-image gets larger sizes to fill space."""
    if has_image:
        if char_count <= 12:  return "130px"
        if char_count <= 20:  return "110px"
        if char_count <= 30:  return "92px"
        if char_count <= 45:  return "76px"
        return "62px"
    else:
        if char_count <= 12:  return "160px"
        if char_count <= 20:  return "138px"
        if char_count <= 30:  return "116px"
        if char_count <= 45:  return "94px"
        return "76px"


def _build_html(post: dict) -> str:
    headline = post.get("headline", "BREAKING NEWS")
    subline  = post.get("subline",  "")
    category = post.get("category", "Breaking").upper()
    keywords = post.get("keywords", [])
    accent   = ACCENT_COLOR

    hl     = _colorize(headline, keywords, accent)
    fsize  = _font_size(len(headline), False)  # calculated below after has_image

    # ── Image ────────────────────────────────────────────────────────────────
    img_path  = post.get("image_path")
    has_image = bool(img_path and Path(img_path).exists())
    img_css   = ""
    if has_image:
        raw    = Path(img_path).read_bytes()
        b64    = base64.b64encode(raw).decode()
        ext    = Path(img_path).suffix.lstrip(".") or "jpeg"
        img_css = f'background-image:url("data:image/{ext};base64,{b64}");background-size:cover;background-position:center;'

    fsize = _font_size(len(headline), has_image)
    shadow = accent + "99"

    # ── Logo footer ───────────────────────────────────────────────────────────
    if _LOGO_B64:
        logo_html = f'<img src="{_LOGO_B64}" style="height:46px;width:auto;object-fit:contain;display:block;"/>'
    else:
        logo_html = f'<span style="font-family:Oswald,sans-serif;font-weight:700;font-size:22px;letter-spacing:4px;color:#fff;">DAILY<span style="color:{accent}">NEWS</span>DROP</span>'

    # ── Layout variants ───────────────────────────────────────────────────────
    if has_image:
        overlay  = f"rgba(10,10,16,0.65)" # Light uniform tint for better visibility
        text_top = "108px"
        text_bot = "88px"
        extra    = ""
    else:
        # No image — subtle top-corner glow, big "DND" watermark, text takes full height
        overlay  = f"radial-gradient(ellipse at 80% 20%, rgba(0,212,232,0.08) 0%, transparent 60%)"
        text_top = "108px"
        text_bot = "88px"
        extra    = f"""
  <!-- Large watermark -->
  <div style="position:absolute;right:-20px;bottom:70px;z-index:3;
              opacity:0.035;font-family:'Oswald',sans-serif;font-size:380px;
              font-weight:700;color:{accent};line-height:1;
              pointer-events:none;user-select:none;letter-spacing:-10px;">
    DND
  </div>
  <!-- Horizontal rule below subline region -->
  <div style="position:absolute;left:44px;right:44px;bottom:100px;z-index:10;
              height:1px;background:linear-gradient(90deg,{accent}55,transparent);"></div>"""

    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"/>
<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@700&family=DM+Sans:wght@400;600&family=DM+Mono:wght@500&display=swap" rel="stylesheet"/>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:1080px;height:1080px;overflow:hidden;background:#0A0A10}}
.post{{position:relative;width:1080px;height:1080px;overflow:hidden;background:#0A0A10}}

/* Image layer */
.img-frame{{position:absolute;inset:0;z-index:1;{img_css}}}

/* Overlay */
.overlay{{position:absolute;inset:0;z-index:2;background:{overlay};}}

/* Left accent bar */
.bar{{position:absolute;left:0;top:0;bottom:0;width:12px;z-index:20;
      background:{accent};box-shadow:0 0 60px {shadow};}}

/* Top-right category badge */
.badge{{position:absolute;top:36px;right:36px;z-index:30;
        background:{accent};color:#000;
        font-family:'DM Mono',monospace;font-weight:500;
        font-size:17px;letter-spacing:3px;text-transform:uppercase;
        padding:8px 18px;border-radius:4px;}}

/* Top-left category pill */
.pill{{position:absolute;top:36px;left:44px;z-index:30;
       display:flex;align-items:center;gap:10px;}}
.dot{{width:12px;height:12px;border-radius:50%;background:{accent};
      flex-shrink:0;box-shadow:0 0 16px {accent};}}
.pill-text{{font-family:'DM Mono',monospace;font-size:18px;font-weight:500;
            letter-spacing:3px;text-transform:uppercase;color:{accent};}}

/* Main text block — vertically centred between badges and footer */
.text-block{{
  position:absolute;
  top:{text_top};left:44px;right:44px;bottom:{text_bot};
  z-index:20;
  display:flex;flex-direction:column;justify-content:center;
}}
.headline{{
  font-family:'Oswald',sans-serif;font-weight:700;
  font-size:{fsize};line-height:0.97;
  color:#FFFFFF;text-transform:uppercase;
  letter-spacing:-1px;word-break:break-word;
  text-shadow:0 4px 48px rgba(0,0,0,0.95);
}}
.headline .hi{{color:{accent};}}
.subline{{
  font-family:'DM Sans',sans-serif;font-weight:400;
  font-size:30px;color:rgba(255,255,255,0.68);
  margin-top:24px;line-height:1.45;
  text-shadow:0 2px 20px rgba(0,0,0,0.95);
}}

/* Footer bar */
.footer{{
  position:absolute;bottom:0;left:0;right:0;height:76px;z-index:30;
  background:rgba(8,8,14,0.98);
  border-top:2px solid {accent};
  display:flex;align-items:center;justify-content:space-between;
  padding:0 36px;
}}
.handle{{font-family:'DM Mono',monospace;font-size:16px;
         color:rgba(255,255,255,0.38);letter-spacing:1px;}}
</style></head><body>
<div class="post">
  <div class="img-frame"></div>
  <div class="overlay"></div>
  <div class="bar"></div>
  {extra}
  <div class="badge">{category}</div>
  <div class="pill">
    <div class="dot"></div>
    <div class="pill-text">{category}</div>
  </div>
  <div class="text-block">
    <div class="headline">{hl}</div>
    <div class="subline">{subline}</div>
  </div>
  <div class="footer">
    {logo_html}
    <div class="handle">{BRAND_HANDLE}</div>
  </div>
</div>
</body></html>"""


def render_post(post: dict) -> str | None:
    """Render post HTML to a 1080x1080 PNG via Playwright. Returns path or None."""
    from playwright.sync_api import sync_playwright

    html     = _build_html(post)
    out_path = POSTS_DIR / f"{post['id']}_post.png"
    tmp_html = POSTS_DIR / f"{post['id']}.html"
    tmp_html.write_text(html, encoding="utf-8")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
            page    = browser.new_page(viewport={"width": 1080, "height": 1080})
            page.goto(f"file://{tmp_html.absolute()}")
            page.wait_for_timeout(3500)   # wait for Google Fonts
            page.screenshot(path=str(out_path),
                            clip={"x": 0, "y": 0, "width": 1080, "height": 1080})
            browser.close()
        tmp_html.unlink(missing_ok=True)
        print(f"  [Render] ✓ {out_path.name}")
        return str(out_path)
    except Exception as e:
        print(f"  [Render] ✗ Error: {e}")
        tmp_html.unlink(missing_ok=True)
        return None
