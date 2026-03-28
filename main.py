"""
main.py — DailyNewsDrop Orchestrator
SPEED FIX: Post generation runs in background threads so handle_replies()
returns instantly. The 5-min reply scheduler never blocks.
"""
import uuid, time, re, threading
from datetime import datetime

import database    as db
from scraper       import fetch_all
from ai_processor  import pre_filter, analyze, analyze_image, generate_from_topic, build_caption
from image_gen     import get_image
from post_renderer import render_post
from mailer        import send_digest, send_post_result, check_for_replies, send_status
from config        import MIN_IMPORTANCE_SCORE, MAX_POSTS_PER_RUN, BRAND_NAME

SEP = "─" * 60
_last_top_articles: list = []   # in-memory cache — also saved to DB for restarts


# ── Pipeline ──────────────────────────────────────────────────────────────────
def run_pipeline():
    global _last_top_articles
    print(f"\n{SEP}")
    print(f"  {BRAND_NAME}  ·  {datetime.now().strftime('%d %b %Y  %H:%M')}")
    print(SEP)

    try:
        articles = fetch_all()
    except Exception as e:
        print(f"[Main] Scraper error: {e}")
        return

    if not articles:
        print("[Main] No new articles.")
        return

    candidates = pre_filter(articles)
    print(f"\n[Main] Scoring {len(candidates)} candidates...")

    scored = []
    for art in candidates:
        print(f"  · {art['title'][:65]}")
        try:
            ai = analyze(art)
        except Exception as e:
            print(f"    → error: {e}")
            ai = None
        if not ai: continue
        score = int(ai.get("importance", 0))
        print(f"    → {score}/10 [{ai.get('category','')}] {ai.get('headline','')[:45]}")
        if score >= MIN_IMPORTANCE_SCORE:
            scored.append((score, art, ai))

    if not scored:
        print("[Main] Nothing passed importance threshold.")
        return

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:MAX_POSTS_PER_RUN]

    _last_top_articles = []
    for score, art, ai in top:
        # Use AI-generated English headline for the digest to keep it readable, 
        # but keep original title for record if needed.
        display_title = ai.get("headline", art["title"])
        _last_top_articles.append({
            "title":     display_title,
            "orig_title": art["title"],
            "source":    art["source"],
            "lang":      art.get("lang", "en"),
            "pub_date":  art.get("pub_date", ""),
            "url":       art["url"],
            "summary":   art.get("summary", ""),
            "image_url": art.get("image_url"),
            "ai":        ai,
            "article":   art,
        })

    # Persist full data to DB — survives restarts
    try:
        db.save_digest(
            [a["title"] for a in _last_top_articles],
            articles_full=_last_top_articles,
        )
    except Exception as e:
        print(f"[Main] DB save error: {e}")

    send_digest(_last_top_articles)
    print(f"\n[Main] Done — digest sent with {len(_last_top_articles)} stories.")


# ── Post generation (runs in background thread) ───────────────────────────────
def _make_and_send_post(article_data: dict, reply_msg_id: str = ""):
    """
    Generate + render + email a single post.
    Always called from a daemon thread — never blocks the reply scheduler.
    """
    pid = str(uuid.uuid4())
    ai  = article_data.get("ai") or {}
    art = article_data.get("article") or article_data

    # If generate_from_topic found a real article, use its image
    source_art = ai.pop("_source_article", None)
    if source_art:
        art = source_art

    uploaded_img = article_data.get("_uploaded_image")
    if uploaded_img:
        img_path = uploaded_img
    else:
        try:
            img_path = get_image(art, pid, ai.get("image_prompt", "news India photorealistic"))
        except Exception as e:
            print(f"  [Post] image error: {e}")
            img_path = None

    # If a manual caption override is provided (from /create form), use it directly
    caption_override = article_data.get("_caption_override", "")
    try:
        caption = caption_override if caption_override else build_caption(ai, art)
    except Exception as e:
        print(f"  [Post] caption error: {e}")
        caption = caption_override or ""

    post = {
        "id":          pid,
        "article_url": art.get("url", ""),
        "headline":    ai.get("headline", art.get("title", "BREAKING NEWS")),
        "subline":     ai.get("subline", ""),
        "caption":     caption,
        "keywords":    ai.get("keywords", []),
        "category":    ai.get("category", "Breaking"),
        "image_path":  img_path,
        "status":      "generated",
    }

    try:
        post_img = render_post(post)
    except Exception as e:
        print(f"  [Post] render error: {e}")
        post_img = None

    if not post_img:
        print(f"  [Post] ✗ Render failed for {pid[:8]}")
        return

    post["post_image_path"] = post_img

    try:
        db.save_post(post)
    except Exception as e:
        print(f"  [Post] DB save error: {e}")

    send_post_result(post, reply_to=reply_msg_id)
    print(f"  [Post] ✅ Done: {post['headline']}")


def _bg_post(article_data, mid):
    """Fire-and-forget post generation in a background thread."""
    try:
        _make_and_send_post(article_data, mid)
    except Exception as e:
        print(f"  [Post] Unhandled error: {e}")


# ── Reply handler ─────────────────────────────────────────────────────────────
def handle_replies():
    """
    FAST: Checks IMAP (seconds), dispatches each reply to a background thread.
    Returns immediately — never blocks the scheduler.
    """
    global _last_top_articles

    # Reload articles from DB if server restarted
    if not _last_top_articles:
        try:
            last = db.get_last_digest()
            if last and last.get("articles_full"):
                _last_top_articles = last["articles_full"]
                print(f"[Replies] Reloaded {len(_last_top_articles)} articles from DB")
        except Exception as e:
            print(f"[Replies] DB reload error: {e}")

    try:
        replies = check_for_replies()
    except Exception as e:
        print(f"[Replies] IMAP error: {e}")
        return

    if not replies:
        print("[Replies] No new replies.")
        return

    print(f"[Replies] {len(replies)} reply(s) — dispatching to background threads")

    for reply in replies:
        text        = reply.get("text", "").strip()
        image_bytes = reply.get("image_bytes")
        mid         = reply.get("message_id", "")

        print(f"[Replies] text='{text[:60]}' image={'yes' if image_bytes else 'no'}")

        # ── Image attachment ──────────────────────────────────────
        if image_bytes:
            print("  → Image — analyzing in background thread...")
            def _do_image(ib=image_bytes, m=mid):
                try:
                    ai = analyze_image(ib)
                    if ai:
                        ai.pop("extracted_text", None)
                        _bg_post({"ai": ai, "article": {"url": "", "source": "User Image", "image_url": None}}, m)
                    else:
                        send_status("[DND] Could not read image",
                            "Could not extract news from image. Try a clearer screenshot or type the topic.")
                except Exception as e:
                    print(f"  [Image reply] Error: {e}")
            threading.Thread(target=_do_image, daemon=True).start()
            if not text:
                continue

        # ── URL ───────────────────────────────────────────────────
        if text.startswith("http"):
            print(f"  → URL — dispatching to background thread")
            def _do_url(t=text, m=mid):
                try:
                    ai = generate_from_topic(t)
                    if ai:
                        _bg_post({"ai": ai, "article": {"url": t, "source": "Custom", "image_url": None}}, m)
                except Exception as e:
                    print(f"  [URL reply] Error: {e}")
            threading.Thread(target=_do_url, daemon=True).start()
            continue

        # ── "all" ─────────────────────────────────────────────────
        if text.lower().strip() == "all":
            print(f"  → all — dispatching {len(_last_top_articles)} posts to background threads")
            for art_data in _last_top_articles:
                def _do_one(ad=art_data, m=mid):
                    try:
                        _bg_post(ad, m)
                        time.sleep(2)
                    except Exception as e:
                        print(f"  [All reply] Error: {e}")
                threading.Thread(target=_do_one, daemon=True).start()
            continue

        # ── Numbers like "1", "2,3", "1 3" ───────────────────────
        clean_text = text.strip()
        nums = re.findall(r"\d+", clean_text)
        if nums and re.match(r"^[\d\s,]+$", clean_text):
            for n in nums:
                idx = int(n) - 1
                if 0 <= idx < len(_last_top_articles):
                    print(f"  → Story #{n} — dispatching to background thread")
                    def _do_num(ad=_last_top_articles[idx], m=mid):
                        try:
                            _bg_post(ad, m)
                        except Exception as e:
                            print(f"  [Num reply] Error: {e}")
                    threading.Thread(target=_do_num, daemon=True).start()
                else:
                    print(f"  → {n} out of range (have {len(_last_top_articles)} stories)")
            continue

        # ── Custom topic — searches real RSS first ────────────────
        if text:
            print(f"  → Custom topic: {text[:60]} — dispatching to background thread")
            def _do_topic(t=text, m=mid):
                try:
                    ai = generate_from_topic(t)
                    if ai:
                        src_art = ai.pop("_source_article", None)
                        art_data = {
                            "ai":      ai,
                            "article": src_art or {"url": "", "source": "Custom", "image_url": None},
                        }
                        _bg_post(art_data, m)
                except Exception as e:
                    print(f"  [Topic reply] Error: {e}")
            threading.Thread(target=_do_topic, daemon=True).start()


if __name__ == "__main__":
    run_pipeline()
