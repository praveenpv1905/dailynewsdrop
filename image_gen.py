import time, urllib.parse, httpx
from pathlib import Path
from config import POSTS_DIR, IMAGE_W, IMAGE_H

_POLLINATIONS = "https://image.pollinations.ai/prompt"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
    "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
    "Referer": "https://www.google.com/",
}

def get_image(article, post_id, img_prompt):
    if isinstance(article, dict) and article.get("image_url"):
        p = _download(article["image_url"], post_id)
        if p: return p
    print(f"  [Image] Generating AI image...")
    return _generate(img_prompt, post_id)

def _download(url, post_id):
    out = POSTS_DIR / f"{post_id}_raw.jpg"
    try:
        r = httpx.get(url, headers=_HEADERS, timeout=20, follow_redirects=True)
        r.raise_for_status()
        if "image" in r.headers.get("content-type","") and len(r.content) > 5000:
            out.write_bytes(r.content)
            print(f"  [Image] Downloaded ✓")
            return str(out)
    except Exception as e:
        print(f"  [Image] Download failed: {e}")
    return None

def _generate(prompt, post_id, retries=3):
    out = POSTS_DIR / f"{post_id}_raw.jpg"
    full = f"{prompt}, photorealistic, high quality, professional news photography, India, cinematic, sharp"
    encoded = urllib.parse.quote(full)
    seed = abs(hash(post_id)) % 99999
    url = f"{_POLLINATIONS}/{encoded}?width={IMAGE_W}&height={IMAGE_H}&nologo=true&model=flux&seed={seed}"
    for attempt in range(retries):
        try:
            print(f"  [Image] Pollinations attempt {attempt+1}...")
            r = httpx.get(url, timeout=120, follow_redirects=True)
            r.raise_for_status()
            if "image" in r.headers.get("content-type",""):
                out.write_bytes(r.content)
                print(f"  [Image] AI-generated ✓")
                return str(out)
        except Exception as e:
            print(f"  [Image] Attempt {attempt+1}: {e}")
            if attempt < retries-1: time.sleep(10)
    _placeholder(out)
    return str(out)

def _placeholder(out):
    # Solid dark image as fallback
    try:
        from PIL import Image
        img = Image.new("RGB", (1080, 1080), color=(15, 15, 20))
        img.save(str(out), "JPEG")
    except Exception:
        out.write_bytes(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9')
