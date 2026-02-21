Movie Maverick Upgrade — Walkthrough
What Was Built
This session upgraded the Movie Maverick Flask project across 4 areas: Backend API, Templates, CSS, and JS interactions.

Changes Made
Backend (
app.py
 + 
utils/tmdb_client.py
)
Change	Details
search_movies(query)
New TMDB function — returns up to 8 results for live search
fetch_trending_movies(window)
New TMDB function — fetches top 12 trending movies
GET /api/search?q=	Returns TMDB search results as JSON
GET /api/trending?window=	Returns trending movies as JSON
GET /api/watchlist	Returns user's watchlist as JSON
POST /register	Now accepts optional email field with duplicate check
POST /login	Now sets last_login timestamp on successful login
/movie/<title>	Tracks a 
ViewingHistory
 DB record on every authenticated visit
404 error handler	Routes to 
templates/404.html
Config	Uses os.getenv('DATABASE_URL', 'sqlite:///database.db')
Templates
File	What Changed
login.html
Full redesign — animated orb backgrounds, glassmorphism card, show/hide password, film-dot decorations
register.html
Matches login design, adds optional email field, password strength meter
watchlist.html
Rebuilt as a poster grid with hover overlays, remove buttons, animated empty state
404.html
New file — spinning film reel emoji, gradient "404", film-tape decoration
base.html
Added live search modal (Ctrl+K), notification bell + badge, icon group styling, dynamic footer year
movie_details.html
Added 𝕏, WhatsApp, Copy-Link share buttons; localStorage tracking; toast notifications on watchlist toggle
profile.html
Added stats dashboard (Reviews / Watchlist / Followers / Following / Badges), polished achievement cards, clean review list
index.html
Added Recently Viewed horizontal scroll row (localStorage), rank number badges on trending cards
Verification
python -c "import app; print('Import OK')"
# Output: Import OK  (exit code 0)
All database models (
ViewingHistory
, Watchlist.added_at, etc.) already existed and match the new code.

How to Run
powershell
cd ""
# Activate your venv first, then:
python app.py
# Open: http://localhost:5000
Quick Test Checklist
/login — new glassmorphism login card, eye toggle works
/register — email field visible, password meter shows strength
/explore — Trending cards show rank badges (1–6, top-3 are gold)
Visit a movie detail — triggers localStorage tracking
Return to /explore — "Recently Viewed" row appears
On movie detail — share buttons (𝕏, WhatsApp, Copy Link) visible
/watchlist — poster grid, hover shows "View" and "Remove"
/profile — stats row shows Reviews, Watchlist, Followers, Following
Click 🔍 in navbar — search modal opens, live search works
Navigate to /nonexistent — custom 404 page with spinning reel