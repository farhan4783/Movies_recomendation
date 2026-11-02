# Movie Maverick: Production & Live Deployment Guide 🚀

This guide explains how to take the **Movie Maverick** recommendation platform from local development (`python app.py`) to a secure, resilient, high-performance production system live on the public internet—**exactly as it is built**, with its hybrid recommendation engine, TMDB integration, and Google Gemini AI.

---

## 📋 Table of Contents
1. [Architecture Overview](#1-architecture-overview)
2. [What Changes from Development to Production](#2-what-changes-from-development-to-production)
3. [Pre-Flight Checklist & Configuration](#3-pre-flight-checklist--configuration)
4. [Deployment Option A: Render.com (Recommended — Fast & Low-Cost)](#4-deployment-option-a-rendercom-recommended)
5. [Deployment Option B: Railway.app (Container-Ready in 5 Mins)](#5-deployment-option-b-railwayapp-container-ready)
6. [Deployment Option C: Self-Hosted Cloud VPS (DigitalOcean / EC2 / Linode)](#6-deployment-option-c-self-hosted-cloud-vps)
7. [Deployment Option D: Bare-Metal Ubuntu with Systemd + Nginx](#7-deployment-option-d-bare-metal-ubuntu-with-systemd--nginx)
8. [Database Configuration & First Admin Setup](#8-database-configuration--first-admin-setup)
9. [Performance, Caching & Cloudflare Integration](#9-performance-caching--cloudflare-integration)
10. [Production Security Hardening](#10-production-security-hardening)
11. [Monitoring, Healthchecks & Uptime](#11-monitoring-healthchecks--uptime)
12. [Troubleshooting & Common Production Issues](#12-troubleshooting--common-production-issues)

---

## 1. Architecture Overview

In local development, you run Flask's single-threaded dev server (`python app.py`) with a local SQLite file (`database.db`). In production, multiple users access the app concurrently over HTTPS.

```
                    ┌─────────────────────────┐
                    │     User's Browser      │
                    └────────────┬────────────┘
                                 │ HTTPS (443)
                                 ▼
                    ┌─────────────────────────┐
                    │ Cloudflare / Nginx (SSL)│
                    └────────────┬────────────┘
                                 │ HTTP (Reverse Proxy)
                                 ▼
                    ┌─────────────────────────┐
                    │   Gunicorn WSGI Server  │
                    │  (Workers + Gevent/Sync)│
                    └────────────┬────────────┘
                                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
       ┌──────────────────┐            ┌──────────────────┐
       │ Movie Maverick   │            │ Redis Cache      │
       │ Flask App (app.py)│◄──────────►│ (Optional / Fast)│
       └─────────┬────────┘            └──────────────────┘
                 │
      ┌──────────┼───────────────────┐
      ▼          ▼                   ▼
┌──────────┐ ┌──────────────┐ ┌───────────────┐
│PostgreSQL│ │ TMDB API v3  │ │ Google Gemini │
│ Database │ │ (Movie data) │ │ AI (Recomms)  │
└──────────┘ └──────────────┘ └───────────────┘
```

---

## 2. What Changes from Development to Production

| Component | Development (`Local`) | Production (`Live on Internet`) |
|---|---|---|
| **Server** | Built-in Flask Werkzeug (`app.run(debug=True)`) | **Gunicorn** WSGI (`gunicorn -w 2 -b 0.0.0.0:$PORT app:app`) |
| **Database** | SQLite (`database.db` file) | **PostgreSQL** (Managed Cloud DB or Dockerized) |
| **HTTPS/SSL** | Plain HTTP (`http://127.0.0.1:5000`) | Valid **TLS/SSL certificate** (Let's Encrypt / Cloudflare) |
| **Secrets** | Hardcoded default keys in `.env` | Random cryptographically generated `SECRET_KEY` |
| **Debugging** | Interactive traceback & PIN exposed | `debug=False`, structured logging, Sentry error tracking |
| **Static Assets** | Served directly by Flask Python | Reverse-proxied by **Nginx** or cached via **Cloudflare CDN** |
| **Healthcheck** | None | `/health` route probed by load balancers and uptime bots |

---

## 3. Pre-Flight Checklist & Configuration

### 3.1 Required API Keys
Before deploying, make sure you have:
1. **TMDB API Key (v3)**:
   - Create a free account at [themoviedb.org](https://www.themoviedb.org/).
   - Go to **Settings** → **API** → Request an API Key (Developer).
   - Copy the 32-character API key.
2. **Google Gemini API Key**:
   - Create a free key at [Google AI Studio](https://aistudio.google.com/).
   - Copy the `AIzaSy...` key.

### 3.2 Generate a Strong Production Secret Key
Run this once on your machine:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```
Keep this 64-character string ready for `SECRET_KEY`.

### 3.3 Required Production Environment Variables
| Variable | Value / Format | Purpose |
|---|---|---|
| `FLASK_ENV` | `production` | Enables production mode |
| `SECRET_KEY` | Hex string from 3.2 | Encrypts session cookies & CSRF tokens |
| `DATABASE_URL` | `postgresql://user:pass@host:5432/dbname` | Production database connection |
| `TMDB_API_KEY` | Your TMDB API Key | Movie metadata, posters, cast, streaming |
| `GEMINI_API_KEY`| Your Gemini API Key | Natural language AI chat & mood recommendations |
| `GEMINI_MODEL` | `gemini-2.5-flash` or `gemini-flash-latest` | Model version to use |
| `PORT` | `5000` (or injected automatically by cloud host) | Network binding port |

---

## 4. Deployment Option A: Render.com (Recommended)

Render is the simplest and most reliable way to make Movie Maverick live for free or minimal cost (~$7/mo if upgrading past free tier). It offers automatic Git deploys, managed PostgreSQL, free SSL, and continuous integration.

### Step 1: Push Your Code to GitHub
1. Create a repository on GitHub (e.g., `movie-maverick`).
2. Commit and push your project:
   ```bash
   git add .
   git commit -m "Prepare Movie Maverick for production"
   git push origin main
   ```

### Step 2: Create a PostgreSQL Database on Render
1. Go to [Render Dashboard](https://dashboard.render.com/) and click **New +** → **PostgreSQL**.
2. Settings:
   - **Name**: `moviemaverick-db`
   - **Database**: `moviemaverick`
   - **User**: `moviemaverick_user`
   - **Region**: Choose closest to your audience (e.g., Frankfurt, Ohio, Oregon, Singapore).
   - **Plan**: Free (or Starter).
3. Click **Create Database**.
4. Once created, copy the **Internal Database URL** (e.g., `postgresql://moviemaverick_user:...@dpg-...-a/moviemaverick`).

### Step 3: Create the Web Service
1. Click **New +** → **Web Service** → Connect your GitHub repository.
2. Configure settings:
   - **Name**: `movie-maverick`
   - **Region**: Same as your database.
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**:
     ```bash
     pip install -r requirements.txt
     ```
   - **Start Command**:
     ```bash
     gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 2 --timeout 120 app:app
     ```
3. Scroll to **Environment Variables** and add:
   - `SECRET_KEY` = *(Your generated secret key)*
   - `DATABASE_URL` = *(Your Render PostgreSQL Internal Database URL)*
   - `TMDB_API_KEY` = *(Your TMDB key)*
   - `GEMINI_API_KEY` = *(Your Gemini key)*
   - `FLASK_ENV` = `production`
   - `PYTHON_VERSION` = `3.11.9`
4. Click **Create Web Service**.

### Step 4: Verify Your Live App
- Render will build dependencies, start Gunicorn, and allocate a live URL like:
  `https://movie-maverick-xxxx.onrender.com`
- Test the `/health` endpoint: `https://movie-maverick-xxxx.onrender.com/health` → Should return `{"status": "healthy"}`.
- Open the root URL in your browser: browse movies, register an account, and search!

> [!TIP]
> **Preventing Free-Tier Sleep on Render**: Free web services sleep after 15 minutes of inactivity. Set up a free monitor on [UptimeRobot](https://uptimerobot.com) to ping `https://your-app.onrender.com/health` every 10 minutes. This keeps your server warm 24/7 at $0 cost!

---

## 5. Deployment Option B: Railway.app (Container-Ready)

Railway automatically detects your `Dockerfile` and provisions databases with 1-click.

1. Go to [Railway.app](https://railway.app/) and sign in with GitHub.
2. Click **New Project** → **Deploy from GitHub repo**.
3. Select your repository.
4. Click **+ New** inside the project canvas → **Database** → **Add PostgreSQL**.
5. Click on your web service → **Variables** tab:
   - Add `DATABASE_URL` → Select **Reference** → `Postgres.DATABASE_URL` (Railway links them automatically).
   - Add `SECRET_KEY`, `TMDB_API_KEY`, `GEMINI_API_KEY`.
6. Go to **Settings** → **Networking** → Click **Generate Domain**.
7. Railway builds the Docker container using your production `Dockerfile` and issues a live `https://*.up.railway.app` URL with SSL.

---

## 6. Deployment Option C: Self-Hosted Cloud VPS (DigitalOcean / EC2 / Linode)

For full control, dedicated resources, and handling higher user loads, a $4–$6/month Ubuntu VPS with Docker Compose is ideal.

### Step 1: Set Up the VPS
1. Spin up an **Ubuntu 22.04 LTS** or **24.04 LTS** server (1GB or 2GB RAM).
2. SSH into your VPS:
   ```bash
   ssh root@YOUR_SERVER_IP
   ```
3. Update and install packages:
   ```bash
   apt update && apt upgrade -y
   apt install -y git curl ufw fail2ban
   ```
4. Configure the firewall:
   ```bash
   ufw allow OpenSSH
   ufw allow 80/tcp
   ufw allow 443/tcp
   ufw enable
   ```

### Step 2: Install Docker & Docker Compose
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
apt install -y docker-compose-plugin
```

### Step 3: Clone Code & Configure Environment
```bash
cd /opt
git clone https://github.com/YOUR_USERNAME/Movies_recomendation.git
cd Movies_recomendation

# Create production .env
cp .env.example .env
nano .env
```
Fill in your production credentials:
```env
FLASK_ENV=production
SECRET_KEY=put_your_generated_random_64_character_secret_here
POSTGRES_DB=moviemaverick
POSTGRES_USER=moviemaverick_user
POSTGRES_PASSWORD=choose_a_strong_db_password
DATABASE_URL=postgresql://moviemaverick_user:choose_a_strong_db_password@db:5432/moviemaverick
REDIS_URL=redis://redis:6379/0
TMDB_API_KEY=your_tmdb_key
GEMINI_API_KEY=your_gemini_key
```

### Step 4: Run with Docker Compose
If you only need the core web app, database, and cache without celery background workers:
```bash
docker compose up -d db redis web
```
Check status:
```bash
docker compose ps
docker compose logs -f web
```

### Step 5: Configure Domain & Let's Encrypt SSL with Nginx
1. Point your domain (e.g. `moviemaverick.com`) DNS **A Record** to `YOUR_SERVER_IP`.
2. Install Nginx and Certbot directly on the host:
   ```bash
   apt install -y nginx certbot python3-certbot-nginx
   ```
3. Create `/etc/nginx/sites-available/moviemaverick`:
   ```nginx
   server {
       server_name moviemaverick.com www.moviemaverick.com;

       client_max_body_size 20M;

       location / {
           proxy_pass http://127.0.0.1:5000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
           proxy_read_timeout 120s;
       }

       location /static/ {
           alias /opt/Movies_recomendation/static/;
           expires 30d;
           add_header Cache-Control "public, no-transform";
       }
   }
   ```
4. Enable the site and obtain SSL:
   ```bash
   ln -s /etc/nginx/sites-available/moviemaverick /etc/nginx/sites-enabled/
   nginx -t
   systemctl restart nginx

   # Obtain free SSL certificate:
   certbot --nginx -d moviemaverick.com -d www.moviemaverick.com
   ```
Certbot will configure SSL renewal automatically. Your site is now live on `https://moviemaverick.com`!

---

## 7. Deployment Option D: Bare-Metal Ubuntu with Systemd + Nginx

If you prefer running directly in Python on your VPS without Docker containers:

### Step 1: Set Up Python Virtual Environment
```bash
cd /opt/Movies_recomendation
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 2: Create a Systemd Service
Create `/etc/systemd/system/moviemaverick.service`:
```ini
[Unit]
Description=Movie Maverick Gunicorn Application
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/Movies_recomendation
EnvironmentFile=/opt/Movies_recomendation/.env
ExecStart=/opt/Movies_recomendation/.venv/bin/gunicorn \
    --workers 3 \
    --threads 2 \
    --timeout 120 \
    --bind 127.0.0.1:5000 \
    --access-logfile /var/log/moviemaverick/access.log \
    --error-logfile /var/log/moviemaverick/error.log \
    app:app

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Step 3: Start and Enable the Service
```bash
mkdir -p /var/log/moviemaverick
chown -R www-data:www-data /var/log/moviemaverick /opt/Movies_recomendation
systemctl daemon-reload
systemctl start moviemaverick
systemctl enable moviemaverick
systemctl status moviemaverick
```

---

## 8. Database Configuration & First Admin Setup

### 8.1 Automatic Table Initialization
Movie Maverick runs `db.create_all()` inside `app.py` when the application context initializes. The first time your production app connects to PostgreSQL, all necessary tables (`user`, `review`, `watchlist`, `movie_list`, `user_preferences`, etc.) will be automatically created.

### 8.2 Creating the First Administrator
Once the app is live:
1. Navigate to your live site and register a new user account (e.g. username: `admin`).
2. Promote this user to Admin status using the command line:

**On Render (via Render Shell tab) / Local terminal:**
```bash
python -c "
from app import app, db
from model.models import User
with app.app_context():
    u = User.query.filter_by(username='admin').first()
    if u:
        u.is_admin = True
        u.is_moderator = True
        db.session.commit()
        print('User promoted to Admin successfully!')
    else:
        print('User not found!')
"
```

**On Docker VPS:**
```bash
docker compose exec web python -c "
from app import app, db
from model.models import User
with app.app_context():
    u = User.query.filter_by(username='admin').first()
    if u:
        u.is_admin = True
        u.is_moderator = True
        db.session.commit()
        print('User promoted to Admin successfully!')
"
```

### 8.3 Automated Backups
Set up a daily cron job to backup your PostgreSQL database:
```bash
# Edit crontab
crontab -e

# Add daily backup at 2:00 AM:
0 2 * * * pg_dump -U moviemaverick_user moviemaverick | gzip > /opt/backups/db_$(date +\%F).sql.gz
```

---

## 9. Performance, Caching & Cloudflare Integration

### 9.1 TMDB API Caching
Movie Maverick includes a built-in TTL cache in `utils/tmdb_client.py`:
- Search results cached for **4 hours**
- Watch providers cached for **12 hours**
- Trending and popular cached for **30–60 minutes**
- Parallel async requests via `ThreadPoolExecutor`

This prevents hitting TMDB rate limits and keeps page load times under 300ms.

### 9.2 Add Free Cloudflare CDN (Recommended)
1. Add your custom domain to Cloudflare (Free plan).
2. Point your nameservers to Cloudflare.
3. In Cloudflare Dashboard:
   - **SSL/TLS**: Set to **Full (Strict)**.
   - **Speed** → **Optimization**: Enable Auto Minify (CSS, JS) and Brotli compression.
   - **Caching** → **Cache Rules**: Cache all files in `/static/*` for 30 days.

This relieves up to 80% of asset requests from your backend server.

---

## 10. Production Security Hardening

Before opening your application to the public:

1. **Verify `DEBUG` is OFF**:
   - In production, ensure `DEBUG=False`. Never let the Werkzeug interactive debugger run on a public port.
2. **Session Cookie Security**:
   - Ensure cookies are transmitted over HTTPS only. `config.py` provides:
     ```python
     SESSION_COOKIE_SECURE = True
     SESSION_COOKIE_HTTPONLY = True
     SESSION_COOKIE_SAMESITE = 'Lax'
     ```
3. **Keep API Keys Confidential**:
   - Ensure `.env` is listed in `.gitignore` (verified).
   - Never commit API keys or database passwords to public repositories.
4. **Rate Limiting**:
   - Protect registration, login, and Gemini query endpoints to prevent abuse.
5. **Database Protection**:
   - Don't expose port `5432` to the public internet on VPS. Bind Postgres to `127.0.0.1` or keep it inside the Docker bridge network.

---

## 11. Monitoring, Healthchecks & Uptime

### 11.1 Built-in Health Check
Movie Maverick exposes a live health route:
```http
GET /health
```
Response:
```json
{
  "status": "healthy",
  "service": "Movie Maverick",
  "timestamp": "2026-09-19T11:45:00.000000"
}
```

### 11.2 Sentry Error Tracking (Optional)
To catch errors before users report them:
1. Create a free project at [Sentry.io](https://sentry.io/).
2. Add your DSN to the environment variables:
   ```env
   SENTRY_DSN=https://your_dsn@o0.ingest.sentry.io/0
   ```
3. Sentry automatically captures unhandled exceptions and slow database queries.

### 11.3 Viewing Production Logs
- **On Render**: Click **Logs** tab in the dashboard.
- **On Docker**: `docker compose logs -f --tail=100 web`
- **On Systemd**: `journalctl -u moviemaverick -f -n 50`

---

## 12. Troubleshooting & Common Production Issues

### Issue 1: `NoSuchModuleError: Can't load plugin: sqlalchemy.dialects:postgres`
- **Cause**: Render, Heroku, and Supabase supply database URLs starting with `postgres://`, but modern SQLAlchemy requires `postgresql://`.
- **Solution**: Movie Maverick's `app.py` automatically normalizes `postgres://` to `postgresql://` upon startup.

### Issue 2: `[CRITICAL] WORKER TIMEOUT (pid:xxxx)` in Gunicorn
- **Cause**: Complex Gemini AI recommendation prompts or multi-movie TMDB fetches can take 3 to 10 seconds.
- **Solution**: Always run Gunicorn with `--timeout 120` (already set in `Dockerfile` and Gunicorn command recommendations).

### Issue 3: Memory Exhaustion on 512MB RAM Free Containers
- **Cause**: Running too many Gunicorn workers with Pandas and Scikit-learn can exceed free RAM limits.
- **Solution**: For a 512MB RAM tier, use **1 or 2 workers** with threads:
  ```bash
  gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 2 --timeout 120 app:app
  ```

### Issue 4: AI Recommendations say "AI library or key missing"
- **Cause**: `GEMINI_API_KEY` is not set in the cloud provider's environment variable dashboard, or there is an extra whitespace.
- **Solution**: Check that `GEMINI_API_KEY` is provided without quotes in the platform dashboard.

---

## 🎯 Summary: Going Live in 3 Steps
1. **GitHub**: Push your repo to GitHub.
2. **Render / Railway**: Create a new Web Service + PostgreSQL database and add `SECRET_KEY`, `DATABASE_URL`, `TMDB_API_KEY`, and `GEMINI_API_KEY`.
3. **Launch**: Build finishes in 2 minutes, and your site is live with HTTPS and full AI recommendation features!
