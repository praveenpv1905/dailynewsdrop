import re, concurrent.futures, feedparser
from datetime import datetime, timezone, timedelta
from config import NEWS_SOURCES, MAX_PER_SOURCE
from database import url_seen, mark_url

_CUTOFF_HOURS = 24

def _clean(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", text).strip()

def _img(entry):
    for m in entry.get("media_content", []):
        if m.get("url"): return m["url"]
    th = entry.get("media_thumbnail", [])
    if th: return th[0].get("url")
    raw = entry.get("summary","") + (entry.get("content",[{"value":""}])[0].get("value",""))
    m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', raw)
    if m and m.group(1).startswith("http"): return m.group(1)
    return None

def _is_fresh(entry) -> bool:
    pp = getattr(entry, "published_parsed", None)
    if not pp: return True
    try:
        pub = datetime(*pp[:6], tzinfo=timezone.utc)
        return pub >= datetime.now(timezone.utc) - timedelta(hours=_CUTOFF_HOURS)
    except Exception:
        return True

def _fetch(source):
    results = []
    skipped_old = 0
    try:
        feed = feedparser.parse(source["url"])
        for e in feed.entries[:MAX_PER_SOURCE]:
            url   = (e.get("link") or "").strip()
            title = _clean(e.get("title") or "")
            if not url or not title: continue
            if url_seen(url): continue
            if not _is_fresh(e):
                skipped_old += 1
                continue
            summary = _clean(e.get("summary") or (e.get("content",[{"value":""}])[0].get("value","")))[:600]
            pub = None
            if getattr(e, "published_parsed", None):
                try: pub = datetime(*e.published_parsed[:6], tzinfo=timezone.utc).isoformat()
                except: pass
            results.append({
                "url": url, "title": title, "summary": summary,
                "source": source["name"], "lang": source.get("lang","en"),
                "priority": source.get("priority",2),
                "image_url": _img(e), "pub_date": pub,
            })
            mark_url(url, title, source["name"])
        if skipped_old:
            print(f"  [24h] Skipped {skipped_old} old from {source['name']}")
    except Exception as e:
        print(f"  [Scraper] {source['name']}: {e}")
    return results


def _already_posted(title: str) -> bool:
    """
    Check if we already generated a post for a very similar story
    by looking at the posts table headlines (last 48h).
    Prevents re-generating the same news twice across pipeline runs.
    """
    words = set(re.findall(r"\b\w{4,}\b", title.lower()))
    if not words: return False
    try:
        from database import _conn
        with _conn() as c:
            rows = c.execute(
                "SELECT headline FROM posts WHERE created_at >= datetime('now', '-48 hours')"
            ).fetchall()
        for row in rows:
            stored = set(re.findall(r"\b\w{4,}\b", (row["headline"] or "").lower()))
            if stored and len(words & stored) / max(len(words | stored), 1) > 0.50:
                return True
    except Exception:
        pass
    return False


def _dedup(articles):
    """Dedup within batch, against recently seen DB titles, and against already-posted headlines."""
    seen, unique = [], []
    for art in articles:
        words = set(re.findall(r"\b\w{4,}\b", art["title"].lower()))
        if not words:
            unique.append(art); continue
        # Within-batch dedup
        if any(len(words & s) / max(len(words | s), 1) > 0.55 for s in seen):
            continue
        # Already generated a post for this story?
        if _already_posted(art["title"]):
            print(f"  [Dedup] Already posted similar story: {art['title'][:60]}")
            continue
        seen.append(words)
        unique.append(art)
    return unique


def fetch_all():
    print(f"[Scraper] Fetching {len(NEWS_SOURCES)} sources (last 24h only)...")
    all_articles = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(_fetch, s): s for s in NEWS_SOURCES}
        for fut in concurrent.futures.as_completed(futures):
            src = futures[fut]
            try:
                arts = fut.result()
                if arts: print(f"  ✓ {src['name']:40s} → {len(arts)} new")
                else:    print(f"  · {src['name']:40s} → no new")
                all_articles.extend(arts)
            except Exception as e:
                print(f"  ✗ {src['name']}: {e}")
    deduped = _dedup(all_articles)
    deduped.sort(key=lambda x: x.get("priority",2))
    print(f"[Scraper] {len(all_articles)} raw → {len(deduped)} after dedup (24h, no repeats)")
    return deduped
