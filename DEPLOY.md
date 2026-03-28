# DailyNewsDrop — Deploy to Railway (Free, Always On)

## Step 1 — Push code to GitHub

1. Go to https://github.com/praveenpv1905
2. Click **New repository** (top right, green button)
3. Name it: `dailynewsdrop`
4. Set to **Private**
5. Click **Create repository**

Now open PowerShell in your `dnd_v5` folder and run:

```powershell
git init
git add .
git commit -m "initial"
git branch -M main
git remote add origin https://github.com/praveenpv1905/dailynewsdrop.git
git push -u origin main
```

If it asks for GitHub login, use your GitHub username and a Personal Access Token
(not your password). Get one at: github.com/settings/tokens → New token → check `repo`.

---

## Step 2 — Deploy on Railway

1. Go to **https://railway.app** and sign up with your GitHub account
2. Click **New Project**
3. Click **Deploy from GitHub repo**
4. Select `praveenpv1905/dailynewsdrop`
5. Railway will detect it automatically and start building

---

## Step 3 — Add Environment Variables

In your Railway project → **Variables** tab → add each one:

| Variable | Value |
|---|---|
| `GMAIL_ADDRESS` | scrollverse.bot@gmail.com |
| `GMAIL_APP_PASS` | itdh knkh eehc bzrz |
| `NOTIFY_EMAIL` | pvpraveen190505@gmail.com |
| `GROQ_API_KEY` | gsk_t4zE4QHu... (from your .env) |
| `WEBHOOK_SECRET` | dnd_secret_2026 |
| `PORT` | 5055 |

Railway sets PORT automatically — you can skip that one actually.

---

## Step 4 — Get Your Public URL

After deploy succeeds:
1. Click **Settings** tab in Railway
2. Under **Domains** → click **Generate Domain**
3. You'll get a URL like `https://dailynewsdrop-production.up.railway.app`

That's your dashboard. Open it in the browser — it's live 24/7.

---

## Step 5 — First Run

Open your Railway URL and click **▶ RUN NOW**.
Within 2-3 minutes you'll get a digest email at pvpraveen190505@gmail.com.

The pipeline auto-runs every 2 hours after that. No action needed.

---

## Updating the code later

Whenever you change something locally:

```powershell
git add .
git commit -m "update"
git push
```

Railway automatically redeploys. Zero downtime.

---

## Free plan limits

Railway free tier gives **$5 credit/month** which covers ~500 hours.
A Flask + Gunicorn app uses roughly $0.003/hour = ~$2/month. Well within free limits.

If you need more, upgrade to Hobby ($5/month) for unlimited.

