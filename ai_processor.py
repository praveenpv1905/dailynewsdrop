"""
ai_processor.py — DailyNewsDrop
Generates news posts. Captions are full factual news reports — no questions,
no engagement bait, no "share this", no "let us know". Just clean news.
"""
import json, time, base64, httpx, re
from config import GROQ_API_KEY, BASE_HASHTAGS, CAPTION_FOOTER, BRAND_NAME

_URL          = "https://api.groq.com/openai/v1/chat/completions"
_MODEL        = "llama-3.3-70b-versatile"
_VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
_DELAY        = 2.0

_HIGH = ["killed","dead","deaths","arrested","blast","explosion","fire","crash",
         "flood","cyclone","earthquake","attack","war","strike","breaking",
         "supreme court","parliament","lok sabha","modi","election","verdict",
         "rbi","sebi","budget","tamil nadu","chennai","dmk","aiadmk","vijay",
         "tvk","sensex","rupee","inflation","isro","iran","pakistan","china"]
_SKIP = ["gold rate today","silver rate today","horoscope","live updates:","live:"]

# Caption instruction block — used in ALL prompts
_CAPTION_RULES = """
CAPTION FORMAT RULES (NON-NEGOTIABLE):
- Write like a professional news reporter filing a report. Factual. Authoritative. Clear.
- Minimum 6 sentences. Cover: what happened, who is involved, where, when, why/how, what happens next or what the impact is.
- Use ALL facts from the source. Do not leave out any detail.
- Do NOT end with a question. Do NOT ask "what do you think?", "comment below", "share this".
- Do NOT use the words: "please", "let us know", "your thoughts", "stay tuned", "follow us", "don't forget".
- Do NOT write phrases like "we want to hear from you" or "tell us in the comments".
- Write in third person. Present tense for ongoing, past tense for completed events.
- End the caption with a final concluding sentence that summarises the significance or what to expect next.
- The caption must be ready to copy-paste directly to Instagram with zero editing needed.
"""


def pre_filter(articles, max_candidates=40):
    scored = []
    for a in articles:
        tl = a["title"].lower()
        if any(s in tl for s in _SKIP): continue
        score = sum(1 for k in _HIGH if k in tl)
        if a.get("priority", 2) == 1: score += 1
        if a.get("lang") == "ta": score += 1
        if score > 0: scored.append((score, a))
    scored.sort(key=lambda x: x[0], reverse=True)
    result = [a for _, a in scored[:max_candidates]]
    print(f"  [Filter] {len(articles)} → {len(result)} candidates")
    return result


def _groq_text(prompt, retries=3):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    body = {"model": _MODEL, "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2048, "temperature": 0.2}
    for attempt in range(retries):
        try:
            r = httpx.post(_URL, headers=headers, json=body, timeout=30)
            if r.status_code == 429:
                wait = 30 * (attempt + 1)
                print(f"  [Groq] Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"  [Groq] Error attempt {attempt+1}: {e}")
            if attempt < retries - 1: time.sleep(5)
    return ""


def _groq_vision(image_bytes: bytes, retries=3) -> str:
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    body = {
        "model": _VISION_MODEL,
        "messages": [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
            {"type": "text", "text": (
                "This is a news post or screenshot. "
                "Extract ALL visible text and information. "
                "Report: what happened, who is involved, where, when, numbers/statistics visible. "
                "Be factual. Only report what you can clearly see in the image."
            )}
        ]}],
        "max_tokens": 1024, "temperature": 0.1,
    }
    for attempt in range(retries):
        try:
            r = httpx.post(_URL, headers=headers, json=body, timeout=60)
            if r.status_code == 429:
                time.sleep(30 * (attempt + 1)); continue
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"  [Vision] Error attempt {attempt+1}: {e}")
            if attempt < retries - 1: time.sleep(5)
    return ""


def _parse_json(raw: str) -> dict | None:
    raw = raw.strip()
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.lower().startswith("json"): raw = raw[4:]
        raw = raw.split("```")[0]
    try:
        return json.loads(raw.strip())
    except Exception:
        return None


def _strip_bad_endings(caption: str) -> str:
    """
    Post-process: remove any question sentences or engagement-bait phrases
    that the AI might still sneak in despite instructions.
    """
    bad_patterns = [
        r"\?[^.]*$",                          # trailing question
        r"what do you think[^.]*\.",
        r"let us know[^.]*\.",
        r"share this[^.]*\.",
        r"comment below[^.]*\.",
        r"your thoughts[^.]*\.",
        r"stay tuned[^.]*\.",
        r"don't forget to[^.]*\.",
        r"please [a-z ]+\.",
        r"we want to hear[^.]*\.",
        r"tell us[^.]*\.",
    ]
    lines = caption.strip().split("\n")
    clean_lines = []
    for line in lines:
        lower = line.lower()
        skip = False
        for pat in bad_patterns:
            if re.search(pat, lower):
                skip = True
                break
        if not skip:
            clean_lines.append(line)
    return "\n".join(clean_lines).strip()


def analyze(article: dict) -> dict | None:
    """Analyze a scraped article. Strict facts, clean news-report caption."""
    time.sleep(_DELAY)
    prompt = f"""You are a senior news editor at '{BRAND_NAME}', a Tamil Nadu & India Instagram news page.

STRICT CONTENT RULES:
- Only use facts explicitly in TITLE and SUMMARY below. Do NOT add anything else.
- If a detail is unclear write "Details awaited" — never guess.

{_CAPTION_RULES}

ARTICLE:
TITLE: {article["title"]}
SOURCE: {article["source"]}
PUBLISHED: {article.get("pub_date","Unknown")}
SUMMARY: {article.get("summary","")[:600]}

Return ONLY valid JSON, no markdown:
{{
  "importance": <1-10 integer>,
  "category": "<Breaking|Politics|Economy|Sports|Tech|Entertainment|Tamil Nadu|India|World>",
  "headline": "<max 8 words, UPPERCASE, punchy — IN ENGLISH>",
  "subline": "<one factual sentence max 14 words — IN ENGLISH>",
  "keywords": ["<2-3 key words from headline to highlight in color>"],
  "image_prompt": "<15-word realistic news photo scene, no text in image>",
  "caption_en": "<IN ENGLISH — 6-8 sentence news report following caption rules above>",
  "caption_ta": "<same full caption accurately translated into Tamil script>",
  "extra_tags": "#tag1 #tag2 #tag3 #tag4"
}}"""

    raw = _groq_text(prompt)
    if not raw: return None
    result = _parse_json(raw)
    if result and result.get("caption_en"):
        result["caption_en"] = _strip_bad_endings(result["caption_en"])
    if result and result.get("caption_ta"):
        result["caption_ta"] = _strip_bad_endings(result["caption_ta"])
    return result


def analyze_image(image_bytes: bytes) -> dict | None:
    """Analyze a news image/screenshot sent by user."""
    print("  [AI] Reading image with vision model...")
    extracted = _groq_vision(image_bytes)
    if not extracted:
        print("  [AI] Vision model returned nothing.")
        return None
    print(f"  [AI] Extracted: {extracted[:120]}...")
    time.sleep(_DELAY)

    prompt = f"""You are a senior news editor at '{BRAND_NAME}', a Tamil Nadu & India Instagram news page.

A user sent a news image/screenshot. Here is what the image shows:
{extracted}

STRICT CONTENT RULES:
- Only use facts from the extracted text above. Do NOT add anything else.
- If a detail is unclear write "Details awaited".

{_CAPTION_RULES}

Return ONLY valid JSON, no markdown:
{{
  "importance": 8,
  "category": "<Breaking|Politics|Economy|Sports|Tech|Entertainment|Tamil Nadu|India|World>",
  "headline": "<max 8 words, UPPERCASE — IN ENGLISH>",
  "subline": "<one factual sentence max 14 words — IN ENGLISH>",
  "keywords": ["<2-3 words to highlight>"],
  "image_prompt": "<15-word realistic news photo scene, no text>",
  "caption_en": "<IN ENGLISH — 6-8 sentence news report following caption rules>",
  "caption_ta": "<same full caption in Tamil script>",
  "extra_tags": "#tag1 #tag2 #tag3 #tag4",
  "extracted_text": "<one-line summary of image content>"
}}"""

    raw = _groq_text(prompt)
    if not raw: return None
    result = _parse_json(raw)
    if result and result.get("caption_en"):
        result["caption_en"] = _strip_bad_endings(result["caption_en"])
    return result


def generate_from_topic(topic: str) -> dict | None:
    """Generate a post from user-provided text. Locked to the exact topic."""
    print(f"  [Topic] Generating post for: {topic[:80]}")
    time.sleep(_DELAY)

    prompt = f"""You are a senior news editor at '{BRAND_NAME}', a Tamil Nadu & India Instagram news page.

The user wants a post about this specific story:

{topic}

STRICT CONTENT RULES:
- Write ONLY about this exact story. Do NOT switch to a different topic.
- Only use facts from the text above. No fabricated quotes or statistics.
- If a detail is unclear write "Details awaited".

{_CAPTION_RULES}

Return ONLY valid JSON, no markdown:
{{
  "importance": 8,
  "category": "<Breaking|Politics|Economy|Sports|Tech|Entertainment|Tamil Nadu|India|World>",
  "headline": "<max 8 words, UPPERCASE, about THIS story — IN ENGLISH>",
  "subline": "<one factual sentence max 14 words — IN ENGLISH>",
  "keywords": ["<2-3 key words from THIS story>"],
  "image_prompt": "<15-word realistic news photo scene matching this story, no text>",
  "caption_en": "<IN ENGLISH — 6-8 sentence news report following caption rules. Cover every available fact.>",
  "caption_ta": "<same full caption accurately in Tamil script>",
  "extra_tags": "#tag1 #tag2 #tag3 #tag4"
}}"""

    raw = _groq_text(prompt)
    if not raw: return None
    result = _parse_json(raw)
    if result and result.get("caption_en"):
        result["caption_en"] = _strip_bad_endings(result["caption_en"])
    return result


def build_caption(ai: dict, article) -> str:
    """Build the full Instagram caption — fully ready to paste, no editing needed."""
    en  = ai.get("caption_en", "")
    ta  = ai.get("caption_ta", "")
    tags = (ai.get("extra_tags", "") + " " + BASE_HASHTAGS).strip()

    src = pub = url = ""
    if isinstance(article, dict):
        src = article.get("source", "")
        pub = article.get("pub_date", "")
        if pub and len(pub) > 10: pub = pub[:10]
        url = article.get("url", "")

    parts = []
    if en:  parts.append(en)
    if ta:  parts.append("\n" + "━" * 16 + "\n" + ta)

    meta = []
    if src: meta.append(f"📰 Source: {src}")
    if pub: meta.append(f"📅 {pub}")
    if url: meta.append(f"🔗 {url}")
    if meta: parts.append("\n" + " | ".join(meta))

    parts.append("\n" + tags)
    parts.append(CAPTION_FOOTER)
    return "\n".join(parts)
