import os, pathlib
from dotenv import load_dotenv
load_dotenv()

BRAND_NAME    = "DailyNewsDrop"
BRAND_SHORT   = "DND"
BRAND_HANDLE  = "@dailynewsdrop"
ACCENT_COLOR  = "#00D4E8"   # cyan — DND identity

GMAIL_ADDRESS  = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASS = os.getenv("GMAIL_APP_PASS")
NOTIFY_EMAIL   = os.getenv("NOTIFY_EMAIL")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

WEBHOOK_SECRET   = os.getenv("WEBHOOK_SECRET", "dnd_secret_2026")
PORT             = int(os.getenv("PORT", 5055))

NEWS_SOURCES = [
    {"name": "The Hindu",                  "url": "https://www.thehindu.com/feeder/default.rss",                           "lang": "en", "priority": 1},
    {"name": "The Hindu - National",       "url": "https://www.thehindu.com/news/national/feeder/default.rss",             "lang": "en", "priority": 1},
    {"name": "Indian Express",             "url": "https://indianexpress.com/feed/",                                       "lang": "en", "priority": 1},
    {"name": "Indian Express - India",     "url": "https://indianexpress.com/section/india/feed/",                         "lang": "en", "priority": 1},
    {"name": "India Today",                "url": "https://www.indiatoday.in/rss/home",                                   "lang": "en", "priority": 1},
    {"name": "NDTV - Top Stories",         "url": "https://feeds.feedburner.com/ndtvnews-top-stories",                    "lang": "en", "priority": 1},
    {"name": "NDTV - India",               "url": "https://feeds.feedburner.com/ndtvnews-india-news",                     "lang": "en", "priority": 1},
    {"name": "Times of India - Top",       "url": "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",           "lang": "en", "priority": 2},
    {"name": "Times of India - India",     "url": "https://timesofindia.indiatimes.com/rssfeeds/296589292.cms",           "lang": "en", "priority": 2},
    {"name": "Hindu Tamil Thisai",         "url": "https://www.hindutamil.in/feed",                                      "lang": "ta", "priority": 1},
    {"name": "Tamil Indian Express",       "url": "https://tamil.indianexpress.com/feed/",                                "lang": "ta", "priority": 1},
    {"name": "Puthiyathalaimurai",         "url": "https://www.puthiyathalaimurai.com/feed",                              "lang": "ta", "priority": 1},
    {"name": "Daily Thanthi",              "url": "https://www.dailythanthi.com/feed",                                    "lang": "ta", "priority": 1},
    {"name": "The Hindu - Tamil Nadu",     "url": "https://www.thehindu.com/news/national/tamil-nadu/feeder/default.rss", "lang": "en", "priority": 1},
    {"name": "The NewsMinute - TN",        "url": "https://www.thenewsminute.com/tamil-nadu/feed",                        "lang": "en", "priority": 1},
]

FETCH_INTERVAL_HOURS = 2
MAX_PER_SOURCE       = 8
MAX_POSTS_PER_RUN    = 20
MIN_IMPORTANCE_SCORE = 6

POLLINATIONS_BASE = "https://image.pollinations.ai/prompt"
IMAGE_W = 1080
IMAGE_H = 1080

BASE_DIR     = pathlib.Path(__file__).resolve().parent
POSTS_DIR    = BASE_DIR / "generated_posts"
DB_PATH      = BASE_DIR / "dnd.db"

POSTS_DIR.mkdir(exist_ok=True)

BASE_HASHTAGS  = "#DailyNewsDrop #DND #TamilNaduNews #IndiaNews #BreakingNews #TamilNews #India #Chennai"
CAPTION_FOOTER = f"\n\n📲 Follow {BRAND_HANDLE} for Tamil Nadu & India news!\n🔔 Turn on notifications."
