# DailyNewsDrop (DND)
Automated Tamil Nadu & India news post generator.

## How it works
Every 2 hours:
1. Scrapes 15 news sources
2. AI scores and filters top stories
3. Sends you a numbered digest email
4. You reply with numbers → posts generated and emailed back
5. Or reply with any topic/URL → custom post generated

## Reply examples
- `1` → generate post for story 1
- `2,4` → generate posts for stories 2 and 4
- `all` → generate all posts
- `Tamil Nadu election results` → custom post on that topic
- `https://instagram.com/p/...` → recreate that post style

## Local setup
```
pip install -r requirements.txt
playwright install chromium
python app.py
```
Dashboard: http://localhost:5055/dashboard

## Deploy to Railway (free, always on)
1. Push this folder to a GitHub repo
2. Go to railway.app → New Project → Deploy from GitHub
3. Add environment variables from .env in Railway dashboard
4. Deploy — Railway gives you a public URL

## Environment variables
GMAIL_ADDRESS, GMAIL_APP_PASS, NOTIFY_EMAIL, GROQ_API_KEY,
WEBHOOK_SECRET, PORT
