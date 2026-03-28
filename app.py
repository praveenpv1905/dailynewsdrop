"""
app.py — DailyNewsDrop Web Server
Flask + APScheduler
"""
import os, sqlite3, base64, threading, json
from pathlib import Path
from flask import Flask, jsonify, request
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
load_dotenv()

import database as db
from config import BRAND_NAME, ACCENT_COLOR, PORT, DB_PATH, BASE_HASHTAGS, CAPTION_FOOTER

app = Flask(__name__)


def _card(r, accent):
    status  = r["status"]
    hl      = (r["headline"] or "").replace("<","&lt;").replace(">","&gt;")
    cat     = r["category"] or ""
    created = (r["created_at"] or "")[:16].replace("T"," ")
    img_p   = r["post_image_path"] or ""
    img_html = ""
    if img_p and Path(img_p).exists():
        data = Path(img_p).read_bytes()
        b64  = base64.b64encode(data).decode()
        img_html = '<img src="data:image/png;base64,' + b64 + '" style="width:100%;border-radius:8px;margin-bottom:12px;display:block"/>'
    sc = {
        "pending": accent, "generated": "#a371f7",
        "approved": "#39d353", "rejected": "#ff5c5c",
        "uploaded": "#39d353", "failed": "#ff5c5c"
    }.get(status, "#9096b8")
    caption  = r["caption"] or ""
    safe_cap = (caption.replace("\\", "\\\\")
                       .replace("`",  "\\`")
                       .replace("$",  "\\$")
                       .replace("\n", "\\n"))
    disp_cap = caption.replace("<","&lt;").replace(">","&gt;")
    cap_html = ""
    if caption:
        cap_html = (
            '<div style="margin-top:12px;background:#0a0a10;border:1px solid #1e1e2a;' +
            'border-radius:8px;padding:12px">' +
            '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">' +
            '<div style="font-size:11px;color:#606075;letter-spacing:1px;font-weight:700">CAPTION</div>' +
            '<button onclick="(function(b){var t=`' + safe_cap + '`.replace(/\\\\n/g,String.fromCharCode(10));navigator.clipboard.writeText(t);b.innerText=\'COPIED✓\';setTimeout(()=>b.innerText=\'COPY\',2000)})(this)" ' +
            'style="background:#1e1e2a;color:' + accent + ';border:1px solid ' + accent + ';border-radius:4px;padding:4px 10px;' +
            'font-size:10px;font-weight:700;cursor:pointer;letter-spacing:1px">COPY</button>' +
            '</div>' +
            '<div style="font-size:12px;color:#c0c8e8;line-height:1.6;white-space:pre-wrap;' +
            'max-height:160px;overflow-y:auto">' + disp_cap + '</div></div>'
        )
    return (
        '<div style="background:#111118;border:1px solid #1e1e2a;border-radius:12px;padding:18px;margin-bottom:14px">' +
        img_html +
        '<div style="font-size:11px;color:' + sc + ';font-weight:700;letter-spacing:2px;margin-bottom:6px">' +
        status.upper() + ' &middot; ' + cat.upper() + ' &middot; ' + created + '</div>' +
        '<div style="font-size:15px;font-weight:700;color:#F0F0F5">' + hl + '</div>' +
        cap_html + '</div>'
    )


@app.route("/")
@app.route("/dashboard")
def dashboard():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows        = conn.execute("SELECT * FROM posts ORDER BY created_at DESC LIMIT 30").fetchall()
    last_digest = conn.execute("SELECT sent_at, articles FROM digest ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()

    if last_digest:
        sent_at = (last_digest["sent_at"] or "")[:16].replace("T"," ")
        try:    count = len(json.loads(last_digest["articles"] or "[]"))
        except: count = 0
        last_run = (
            '<div style="background:#111118;border:1px solid #1e1e2a;border-radius:12px;' +
            'padding:16px 22px;margin-bottom:20px;display:flex;align-items:center;gap:14px">' +
            '<div style="width:9px;height:9px;border-radius:50%;background:' + ACCENT_COLOR +
            ';box-shadow:0 0 10px ' + ACCENT_COLOR + ';flex-shrink:0"></div>' +
            '<div><div style="font-size:11px;color:#606075;letter-spacing:1px">LAST RUN</div>' +
            '<div style="font-size:14px;color:#F0F0F5;margin-top:2px">' + sent_at +
            ' &middot; ' + str(count) + ' stories sent</div></div></div>'
        )
    else:
        last_run = (
            '<div style="background:#111118;border:1px solid #1e1e2a;border-radius:12px;' +
            'padding:16px 22px;margin-bottom:20px;display:flex;align-items:center;gap:14px">' +
            '<div style="width:9px;height:9px;border-radius:50%;background:#404050;flex-shrink:0"></div>' +
            '<div><div style="font-size:11px;color:#606075;letter-spacing:1px">LAST RUN</div>' +
            '<div style="font-size:14px;color:#606075;margin-top:2px">Never — hit RUN NOW</div></div></div>'
        )

    cards = "".join(_card(r, ACCENT_COLOR) for r in rows) or             '<div style="color:#606075;text-align:center;padding:60px 0">No posts yet.</div>'

    A = ACCENT_COLOR
    return (
        '<!DOCTYPE html><html><head><meta charset="UTF-8"/><title>DND Dashboard</title>' +
        '<meta http-equiv="refresh" content="30"/>' +
        '<style>body{font-family:-apple-system,sans-serif;background:#0a0a10;color:#F0F0F5;margin:0;padding:20px}' +
        '.btn{display:inline-block;padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:700;font-size:13px;letter-spacing:1px;white-space:nowrap}' +
        '</style></head><body>' +
        '<div style="max-width:600px;margin:0 auto">' +
        '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:24px;flex-wrap:wrap;gap:12px">' +
        '<div><div style="font-size:22px;font-weight:700;letter-spacing:3px;color:' + A + '">' +
        'DAILY<span style="color:#fff">NEWS</span>DROP</div>' +
        '<div style="font-size:11px;color:#606075;letter-spacing:1px;margin-top:2px">DASHBOARD &middot; AUTO-REFRESHES EVERY 30s</div></div>' +
        '<div style="display:flex;gap:8px;flex-wrap:wrap">' +
        '<a href="/run"           class="btn" style="background:' + A + ';color:#000">&#9654; RUN NOW</a>' +
        '<a href="/create"        class="btn" style="background:#181828;color:#a371f7;border:1px solid #a371f7">&#9998; CREATE POST</a>' +
        '<a href="/check-replies" class="btn" style="background:#1e1e2a;color:' + A + ';border:1px solid ' + A + '">&#128235; CHECK REPLIES</a>' +
        '</div></div>' +
        last_run + cards +
        '</div></body></html>'
    )


@app.route("/create", methods=["GET"])
def create_page():
    cats = ["Breaking","Politics","Economy","Sports","Tech","Entertainment","Tamil Nadu","India","World"]
    cat_opts = "".join('<option value="' + c + '">' + c + '</option>' for c in cats)
    A = ACCENT_COLOR
    return (
        '<!DOCTYPE html><html><head><meta charset="UTF-8"/><title>Create Post — DND</title>' +
        '<style>' +
        '*{box-sizing:border-box}' +
        'body{font-family:-apple-system,sans-serif;background:#0a0a10;color:#F0F0F5;margin:0;padding:20px}' +
        '.wrap{max-width:600px;margin:0 auto}' +
        'label{display:block;font-size:11px;color:#606075;letter-spacing:1.5px;font-weight:700;margin-bottom:6px;margin-top:20px}' +
        'input,textarea,select{width:100%;background:#111118;border:1px solid #1e1e2a;border-radius:8px;' +
        'color:#F0F0F5;padding:12px 14px;font-size:14px;font-family:inherit;outline:none}' +
        'input:focus,textarea:focus,select:focus{border-color:' + A + '}' +
        'textarea{resize:vertical;line-height:1.6}' +
        '.hint{font-size:11px;color:#404055;margin-top:4px}' +
        '.row{display:flex;gap:12px} .row>div{flex:1}' +
        '.submit-btn{margin-top:28px;width:100%;padding:14px;background:' + A + ';color:#000;' +
        'border:none;border-radius:8px;font-size:15px;font-weight:700;cursor:pointer;letter-spacing:1px}' +
        '.submit-btn:disabled{opacity:0.5;cursor:not-allowed}' +
        '.ai-btn{margin-top:12px;width:100%;padding:12px;background:#181828;color:#a371f7;' +
        'border:1px solid #a371f7;border-radius:8px;font-size:14px;font-weight:700;cursor:pointer}' +
        '.section{font-size:14px;font-weight:700;color:#fff;margin-top:28px;padding-bottom:10px;border-bottom:1px solid #1e1e2a}' +
        '.spinner{display:none;text-align:center;padding:16px;color:' + A + '}' +
        'select option{background:#111118}' +
        'a.back{color:' + A + ';text-decoration:none;font-size:13px;display:inline-block;margin-bottom:20px}' +
        '</style></head><body><div class="wrap">' +
        '<a href="/dashboard" class="back">&#8592; Dashboard</a>' +
        '<div style="font-size:20px;font-weight:700;color:' + A + ';letter-spacing:2px;margin-bottom:4px">CREATE POST</div>' +
        '<div style="font-size:12px;color:#606075;margin-bottom:4px">Fill the form manually, or paste a news story and let AI fill it.</div>' +

        '<div style="background:#111118;border:1px solid #1e1e2a;border-radius:12px;padding:18px;margin:20px 0">' +
        '<div style="font-size:13px;font-weight:700;color:#a371f7;letter-spacing:1px;margin-bottom:10px">✨ AI AUTO-FILL</div>' +
        '<div style="font-size:13px;color:#9096b8;margin-bottom:12px">Paste a news headline, story text, or topic — AI fills the whole form for you.</div>' +
        '<textarea id="ai_topic" rows="3" placeholder="e.g. Bus accident in Bangladesh while boarding a ferry, 15 killed..."' +
        ' style="width:100%;background:#0a0a10;border:1px solid #1e1e2a;border-radius:8px;' +
        'color:#F0F0F5;padding:12px;font-size:13px;font-family:inherit;resize:vertical"></textarea>' +
        '<button class="ai-btn" onclick="aiAutofill()">✨ Auto-fill with AI</button>' +
        '<div class="spinner" id="ai_spinner">&#9203; AI is filling the form...</div>' +
        '</div>' +

        '<form id="postForm" method="POST" action="/create" enctype="multipart/form-data">' +

        '<div class="section">POST CONTENT</div>' +
        '<label>HEADLINE *</label>' +
        '<input type="text" name="headline" id="f_headline" maxlength="80" placeholder="e.g. BUS ACCIDENT KILLS 15 IN BANGLADESH" required/>' +
        '<div class="hint">Keep it short and punchy. Auto-uppercased on the post.</div>' +

        '<label>SUBLINE</label>' +
        '<input type="text" name="subline" id="f_subline" maxlength="120" placeholder="e.g. Ferry boarding tragedy claims lives near Dhaka"/>' +
        '<div class="hint">One sentence below the headline.</div>' +

        '<div class="row">' +
        '<div><label>CATEGORY</label><select name="category" id="f_category">' + cat_opts + '</select></div>' +
        '<div><label>HIGHLIGHT KEYWORDS</label>' +
        '<input type="text" name="keywords" id="f_keywords" placeholder="bus, Bangladesh, accident"/>' +
        '<div class="hint">Comma-separated. These turn cyan on the post.</div></div>' +
        '</div>' +

        '<div class="section">CAPTIONS</div>' +
        '<label>ENGLISH CAPTION *</label>' +
        '<textarea name="caption_en" id="f_caption_en" rows="6" ' +
        'placeholder="Write 4-6 sentences for Instagram. End with a question to drive engagement." required></textarea>' +
        '<label>TAMIL CAPTION</label>' +
        '<textarea name="caption_ta" id="f_caption_ta" rows="5" ' +
        'placeholder="Same caption in Tamil (AI fills this automatically)"></textarea>' +

        '<div class="section">IMAGE</div>' +
        '<label>UPLOAD IMAGE <span style="color:#606075;font-weight:400">(optional — overrides URL and AI)</span></label>' +
        '<input type="file" name="image_file" id="f_image_file" accept="image/*" style="margin-bottom:10px"/>' +
        '<label>IMAGE URL <span style="color:#606075;font-weight:400">(optional — leave blank to generate AI image)</span></label>' +
        '<input type="url" name="image_url" id="f_image_url" placeholder="https://example.com/photo.jpg"/>' +
        '<label>AI IMAGE PROMPT <span style="color:#606075;font-weight:400">(if generating image)</span></label>' +
        '<input type="text" name="image_prompt" id="f_image_prompt" placeholder="e.g. overturned bus near river dock Bangladesh"/>' +

        '<div class="section">HASHTAGS</div>' +
        '<label>EXTRA HASHTAGS</label>' +
        '<input type="text" name="extra_tags" id="f_extra_tags" placeholder="#Bangladesh #BusAccident"/>' +
        '<div class="hint">Default DND hashtags always added. Just add topic-specific ones here.</div>' +

        '<button type="submit" class="submit-btn" id="submitBtn">&#128247; GENERATE &amp; SEND POST</button>' +
        '</form>' +
        '<div id="submitting" class="spinner" style="margin-top:0">&#9203; Generating post (~60s). Check your email in ~60s.</div>' +

        '<script>' +
        'document.getElementById("postForm").addEventListener("submit",function(){' +
        'document.getElementById("submitBtn").disabled=true;' +
        'document.getElementById("submitting").style.display="block";' +
        '});' +
        'async function aiAutofill(){' +
        'const topic=document.getElementById("ai_topic").value.trim();' +
        'if(!topic){alert("Please enter a topic first.");return;}' +
        'document.querySelector(".ai-btn").disabled=true;' +
        'document.getElementById("ai_spinner").style.display="block";' +
        'try{' +
        'const r=await fetch("/ai-fill",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({topic})});' +
        'const d=await r.json();' +
        'if(d.error){alert("AI error: "+d.error);return;}' +
        'if(d.headline)   document.getElementById("f_headline").value=d.headline;' +
        'if(d.subline)    document.getElementById("f_subline").value=d.subline;' +
        'if(d.category)   document.getElementById("f_category").value=d.category;' +
        'if(d.keywords)   document.getElementById("f_keywords").value=(d.keywords||[]).join(", ");' +
        'if(d.caption_en) document.getElementById("f_caption_en").value=d.caption_en;' +
        'if(d.caption_ta) document.getElementById("f_caption_ta").value=d.caption_ta;' +
        'if(d.image_prompt)document.getElementById("f_image_prompt").value=d.image_prompt;' +
        'if(d.extra_tags) document.getElementById("f_extra_tags").value=d.extra_tags;' +
        '}catch(e){alert("Failed: "+e.message);}' +
        'finally{' +
        'document.querySelector(".ai-btn").disabled=false;' +
        'document.getElementById("ai_spinner").style.display="none";' +
        '}' +
        '}' +
        '</script></div></body></html>'
    )


@app.route("/ai-fill", methods=["POST"])
def ai_fill():
    try:
        data  = request.get_json(force=True)
        topic = (data.get("topic") or "").strip()
        if not topic:
            return jsonify({"error": "No topic provided"})
        from ai_processor import generate_from_topic
        result = generate_from_topic(topic)
        if not result:
            return jsonify({"error": "AI could not process this. Try again."})
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/create", methods=["POST"])
def create_submit():
    headline     = request.form.get("headline", "").strip().upper()
    subline      = request.form.get("subline",  "").strip()
    category     = request.form.get("category", "Breaking").strip()
    keywords     = [k.strip() for k in request.form.get("keywords","").split(",") if k.strip()]
    caption_en   = request.form.get("caption_en",  "").strip()
    caption_ta   = request.form.get("caption_ta",  "").strip()
    image_url    = request.form.get("image_url",   "").strip()
    image_prompt = request.form.get("image_prompt","").strip() or headline.lower() + " news photorealistic"
    extra_tags   = request.form.get("extra_tags",  "").strip()
    image_file   = request.files.get("image_file")
    
    uploaded_image_path = None
    if image_file and image_file.filename:
        import uuid
        from pathlib import Path
        Path("generated_posts").mkdir(exist_ok=True)
        uploaded_image_path = f"generated_posts/{uuid.uuid4()}_upload.png"
        image_file.save(uploaded_image_path)

    if not headline or not caption_en:
        return '<h3 style="color:red">Headline and English caption are required.</h3><a href="/create">Back</a>'

    parts = [caption_en]
    if caption_ta:
        parts.append("\n" + "\u2501" * 16 + "\n" + caption_ta)
    parts.append("\n" + (extra_tags + " " + BASE_HASHTAGS).strip())
    parts.append(CAPTION_FOOTER)
    full_caption = "\n".join(parts)

    ai_data = {
        "headline": headline, "subline": subline, "category": category,
        "keywords": keywords, "image_prompt": image_prompt,
        "caption_en": caption_en, "caption_ta": caption_ta, "extra_tags": extra_tags,
    }
    article = {"url": "", "source": "Manual", "image_url": image_url or None, "pub_date": ""}

    def _bg():
        try:
            from main import _make_and_send_post
            _make_and_send_post(
                {"ai": ai_data, "article": article, "_caption_override": full_caption, "_uploaded_image": uploaded_image_path},
                reply_msg_id=""
            )
        except Exception as e:
            print(f"[Create] Error: {e}")
    threading.Thread(target=_bg, daemon=True).start()

    A = ACCENT_COLOR
    return (
        '<html><body style="background:#0a0a10;color:#fff;font-family:sans-serif;' +
        'display:flex;align-items:center;justify-content:center;height:100vh;margin:0">' +
        '<div style="text-align:center;max-width:400px">' +
        '<div style="font-size:48px">&#127775;</div>' +
        '<div style="font-size:22px;font-weight:700;margin:14px 0">Post queued!</div>' +
        '<div style="font-size:14px;color:#9096b8;line-height:1.6;margin-bottom:24px">' +
        'Generating your post and sending to your email.<br/>Takes about 60 seconds.</div>' +
        '<a href="/create" style="color:' + A + ';margin-right:20px">+ Create another</a>' +
        '<a href="/dashboard" style="color:' + A + '">&#8592; Dashboard</a>' +
        '</div></body></html>'
    )


@app.route("/run")
def run_now():
    def _bg():
        try:
            from main import run_pipeline
            run_pipeline()
        except Exception as e:
            print(f"[Run] Error: {e}")
    threading.Thread(target=_bg, daemon=True).start()
    A = ACCENT_COLOR
    return (
        '<html><body style="background:#0a0a10;color:#fff;font-family:sans-serif;' +
        'display:flex;align-items:center;justify-content:center;height:100vh;margin:0">' +
        '<div style="text-align:center"><div style="font-size:48px">&#9889;</div>' +
        '<div style="font-size:20px;margin:12px 0">Fetching latest news...</div>' +
        '<div style="font-size:13px;color:#606075;margin-bottom:20px">Digest will arrive in your email shortly.</div>' +
        '<a href="/dashboard" style="color:' + A + '">&#8592; Dashboard</a></div></body></html>'
    )


@app.route("/check-replies")
def check_replies_now():
    def _bg():
        try:
            from main import handle_replies
            handle_replies()
        except Exception as e:
            print(f"[Replies] Error: {e}")
    threading.Thread(target=_bg, daemon=True).start()
    A = ACCENT_COLOR
    return (
        '<html><body style="background:#0a0a10;color:#fff;font-family:sans-serif;' +
        'display:flex;align-items:center;justify-content:center;height:100vh;margin:0">' +
        '<div style="text-align:center"><div style="font-size:48px">&#128235;</div>' +
        '<div style="font-size:20px;margin:12px 0">Checking replies...</div>' +
        '<div style="font-size:13px;color:#606075;margin-bottom:20px">Watch terminal for logs.</div>' +
        '<a href="/dashboard" style="color:' + A + '">&#8592; Dashboard</a></div></body></html>'
    )


@app.route("/health")
def health():
    return jsonify({"status": "ok", "brand": BRAND_NAME})


def _sched_replies():
    try:
        from main import handle_replies
        handle_replies()
    except Exception as e:
        print(f"[Scheduler] Reply error: {e}")


scheduler = BackgroundScheduler()
scheduler.add_job(_sched_replies, "interval", minutes=5, id="replies")
scheduler.start()
print("[App] Ready — dashboard at /dashboard | create post at /create | replies every 5min")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=False)
