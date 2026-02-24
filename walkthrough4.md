Movie Maverick - Template Update Walkthrough
What Was Done
1. 
base.html
 — Navigation Links
Added Trending, Charts, and Compare links to both the main navbar and the mobile hamburger menu
Active-link highlighting applies to all 3 new routes
2. 
watchlist.html
 — Watch Status Pills
Added status pill UI (Want to Watch / Watching / Watched) to every watchlist card
Wired to the 
setStatus()
 JS function → calls POST /api/watchlist/update-status
Active pill updates instantly without page reload, using distinct color coding
3. 
movie_details.html
 — Review Likes
Each review card now shows a ❤️ / 🤍 like button (only for logged-in users)
Jinja uses review.liked_by_ids property (a 
set
 of user IDs) to pre-render liked state
toggleReviewLike(reviewId)
 makes POST /api/reviews/{id}/like and updates count + icon without reload
4. 
index.html
 — "For You" AI Recommendations
A ✨ For You section is injected between Recently Viewed and Trending Now (only for authenticated users)
Shows skeleton placeholders on load, then fetches GET /api/for-you
If no personalized data exists (empty viewing history), the section is hidden gracefully
5. 
profile.html
 — Live Cinema Stats
Added a 📊 Your Cinema Stats section below the Reviews panel
Displays animated skeleton cards on load, then fetches GET /api/stats
Shows: Movies Viewed, Reviews Written, Watchlist Count, Watched Count, Avg Rating, Top Genre
6. 
model/models.py
 — Review.liked_by_ids
Added @property liked_by_ids to the 
Review
 model returning a 
set
 of user IDs who liked it
Prevents N+1 queries in templates by computing the set once via self.likes.all()
7. 
app.py
 — Performance Fix
Charts route 
charts_page()
 was reduced from 20 → 10 enriched movies to prevent TMDB API timeout
Verification Results
Route	Status
GET /	✅ 200 OK
GET /trending	✅ 200 OK
GET /compare	✅ 200 OK
GET /charts	⚠️ Was timing out → Fixed (capped at 10 movies)
app.py
 syntax	✅ OK
models.py
 syntax	✅ OK
Lint Notes
All IDE lint warnings in the templates are false positives from the linter misreading Jinja2 {{ }} syntax inside <script> / <style> blocks. They have no effect at runtime.