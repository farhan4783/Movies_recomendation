from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import pandas as pd
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
import os
from datetime import datetime
from collections import Counter

from model.recommenders import PopularityRecommender, ContentBasedRecommender, CollaborativeRecommender, HybridRecommender
from model.ai_recommender import get_ai_recommendation, get_mood_recommendation, get_user_personality
from utils.tmdb_client import fetch_movie_details, fetch_popular_movies, fetch_full_movie_details, fetch_full_movie_details_by_id, search_movies, fetch_trending_movies
from model import db
from model.models import User, Watchlist, Review, MovieList, ListItem, ViewingHistory, ReviewLike
from utils.achievements import initialize_achievements, check_and_award_achievements, get_achievement_progress

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "super_secret_key_change_this")

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False

db.init_app(app)

# Login Manager Configuration
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create Database Tables
with app.app_context():
    db.create_all()
    # Initialize achievements
    initialize_achievements()

# Load Data Globaly
try:
    # Use enriched data for filtering capabilities
    movies_df = pd.read_csv("data/movies_enriched.csv")
    ratings_df = pd.read_csv("data/ratings.csv")
    
    # Initialize Models
    print("Initializing Models...")
    pop_model = PopularityRecommender(movies_df, ratings_df)
    content_model = ContentBasedRecommender(movies_df)
    collab_model = CollaborativeRecommender(movies_df, ratings_df)
    hybrid_model = HybridRecommender(content_model, collab_model, pop_model)
    print("Models Initialized.")
except Exception as e:
    print(f"Error loading models: {e}")
    # Fallback for safe startup if data is missing
    movies_df = pd.DataFrame()
    pop_model = None

@app.route("/")
def index():
    """Landing page - About Movie Maverick"""
    return render_template("about.html", user=current_user)

@app.route("/explore", methods=["GET", "POST"])
def explore_page():
    recommendations = []
    selected_movie = None
    selected_movies = []
    error = None
    popular_movies_display = []

    # Get Popular movies for default view
    if pop_model:
        # Get top 10 titles
        pop_titles = pop_model.recommend(n=6)
        # Fetch details for them
        for title in pop_titles:
            details = fetch_movie_details(title)
            if details:
                popular_movies_display.append(details)
            else:
                popular_movies_display.append({
                    "title": title,
                    "poster_path": "https://via.placeholder.com/200x300?text=No+Image",
                    "vote_average": "N/A",
                    "release_date": ""
                })

    if request.method == "POST":
        selected_movie = request.form.get("movie")
        
        # Get Filters
        filter_genre = request.form.get("genre")
        filter_min_year = request.form.get("min_year")
        filter_min_rating = request.form.get("min_rating")

        try:
            current_user_id = current_user.id if current_user.is_authenticated else 1
            
            # Handle multi-movie selection
            selected_movies_json = request.form.get("selected_movies")
            if selected_movies_json:
                import json
                try:
                    selected_movies = json.loads(selected_movies_json)
                except:
                    selected_movies = [selected_movies_json] # Fallback
            else:
                 val = request.form.get("movie")
                 selected_movies = [val] if val else []

            if not selected_movies:
                 error = "Please select at least one movie."
            else:
                # Request more candidates to allow for filtering
                # If we filter, we need a larger pool
                candidate_pool_size = 50 if (filter_genre or filter_min_year or filter_min_rating) else 5
                
                raw_recs = hybrid_model.recommend(selected_movies, current_user_id, n=candidate_pool_size)
                
                # Apply Filters
                filtered_recs = []
                for title in raw_recs:
                    movie_row = movies_df[movies_df['title'] == title].iloc[0]
                    
                    # Check Genre
                    if filter_genre and filter_genre != "All" and filter_genre not in str(movie_row['genre']):
                        continue
                        
                    # Check Year
                    if filter_min_year:
                        try:
                            if int(movie_row['year']) < int(filter_min_year):
                                continue
                        except:
                            pass # specific error handling if year is N/A
                            
                    # Check Rating
                    if filter_min_rating:
                        try:
                            # Use our local avg_rating which we computed
                            if float(movie_row['avg_rating']) < float(filter_min_rating):
                                continue
                        except:
                            pass
                            
                    filtered_recs.append(title)
                    if len(filtered_recs) >= 5: # Stop after finding 5 good matches
                        break
                
                # If we filtered too much and got nothing, fallback to top raw results but warn user?
                # Or just show what we found.
                if not filtered_recs and raw_recs:
                     error = "No movies matched your strict filters. Showing unmatched recommendations."
                     filtered_recs = raw_recs[:5]
                elif not filtered_recs:
                     error = "No recommendations found."

                # Fetch details for filtered recommendations
                for title in filtered_recs:
                    details = fetch_movie_details(title)
                    if details:
                        recommendations.append(details)
                    else:
                        movie_row = movies_df[movies_df['title'] == title].iloc[0]
                        recommendations.append({
                            "title": title,
                            "poster_path": "https://via.placeholder.com/200x300?text=No+Image",
                            "vote_average": movie_row.get('avg_rating', 'N/A'),
                            "release_date": str(movie_row.get('year', ''))
                        })
                    
            if not recommendations and not error:
                error = "Could not find recommendations for this movie."
                
        except Exception as e:
            error = f"Error: {str(e)}"
            print(e)
            import traceback
            traceback.print_exc()

    # Get Genres for dropdown
    genres = sorted(movies_df['genre'].dropna().unique().tolist()) if not movies_df.empty else []
    movie_list = movies_df[['title']].to_dict('records') if not movies_df.empty else []

    return render_template(
        "index.html",
        movies=movie_list,
        recommendations=recommendations,
        selected_movie=selected_movies if isinstance(selected_movies, list) else selected_movies,
        popular_movies=popular_movies_display,
        error=error,
        user=current_user,
        genres=genres
    )

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            user.last_login = datetime.utcnow()
            db.session.commit()
            login_user(user)
            return redirect(url_for('explore_page'))
        else:
            return render_template('login.html', error='Invalid username or password')
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email', '').strip() or None
        
        user = User.query.filter_by(username=username).first()
        if user:
            return render_template('register.html', error='Username already exists')
        
        if email:
            existing_email = User.query.filter_by(email=email).first()
            if existing_email:
                return render_template('register.html', error='Email already registered')
        
        new_user = User(username=username, password=generate_password_hash(password, method='scrypt'), email=email)
        db.session.add(new_user)
        db.session.commit()
        
        login_user(new_user)
        return redirect(url_for('explore_page'))
        
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile():
    from utils.achievements import get_achievement_progress
    reviews = Review.query.filter_by(user_id=current_user.id).order_by(Review.created_at.desc()).all()
    watchlist_count = Watchlist.query.filter_by(user_id=current_user.id).count()
    achievement_progress = get_achievement_progress(current_user.id)
    return render_template('profile.html', user=current_user, reviews=reviews, watchlist_count=watchlist_count, achievements=achievement_progress)

@app.route('/api/profile/update', methods=['POST'])
@login_required
def update_profile():
    data = request.get_json()
    bio = data.get('bio')
    avatar_url = data.get('avatar_url')
    
    if bio:
        current_user.bio = bio
    if avatar_url:
        current_user.avatar_url = avatar_url
        
    db.session.commit()
    return jsonify({'success': True, 'message': 'Profile updated successfully'})

@app.route("/api/chat", methods=["POST"])
def ai_chat():
    data = request.get_json()
    user_query = data.get("query")
    
    if not user_query:
        return jsonify({"response": "Please say something!"})
        
    response = get_ai_recommendation(user_query)
    return jsonify({"response": response})

@app.route("/chat")
def chat_page():
    return render_template("chat.html", user=current_user)

@app.route("/api/personality")
@login_required
def api_personality():
    """Analyze current user's movie personality based on history"""
    # Get movie titles from viewing history and reviews
    history = ViewingHistory.query.filter_by(user_id=current_user.id).all()
    reviews = Review.query.filter_by(user_id=current_user.id).all()
    
    movie_titles = list(set([h.movie_title for h in history] + [r.movie_title for r in reviews]))
    
    personality = get_user_personality(movie_titles)
    return jsonify(personality)

@app.route("/modyverse")
def modyverse_page():
    return render_template("modyverse.html", user=current_user)

@app.route("/api/modyverse", methods=["POST"])
def api_modyverse():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    response_html = get_mood_recommendation(data)
    return jsonify({"html": response_html})

@app.route("/movie/id/<int:tmdb_id>")
def movie_details_by_id(tmdb_id):
    """Fetch movie details by TMDB ID — reliable, avoids URL encoding issues."""
    details = fetch_full_movie_details_by_id(tmdb_id)

    if not details:
        return render_template("404.html", user=current_user), 404

    return _render_movie_details(details)


@app.route("/movie/<path:title>")
def movie_details(title):
    """Fetch movie details by title (legacy / fallback route)."""
    details = fetch_full_movie_details(title)

    if not details:
        return render_template("404.html", user=current_user), 404

    return _render_movie_details(details)


def _render_movie_details(details):
    """Shared logic for rendering movie details page."""
    in_watchlist = False
    if current_user.is_authenticated:
        exists = Watchlist.query.filter_by(user_id=current_user.id, movie_title=details['title']).first()
        if exists:
            in_watchlist = True
        # Track viewing history
        try:
            history = ViewingHistory(
                user_id=current_user.id,
                movie_title=details['title'],
                tmdb_id=details.get('id')
            )
            db.session.add(history)
            db.session.commit()
        except Exception:
            db.session.rollback()

    reviews = Review.query.filter_by(movie_title=details['title']).order_by(Review.created_at.desc()).all()

    # Attach like counts and whether current user liked each review
    for review in reviews:
        review.like_count = review.get_like_count()
        review.liked_by_me = review.is_liked_by(current_user) if current_user.is_authenticated else False

    return render_template("movie_details.html", movie=details, in_watchlist=in_watchlist, user=current_user, reviews=reviews)

@app.route("/api/submit_review", methods=["POST"])
@login_required
def submit_review():
    data = request.get_json()
    movie_title = data.get("movie_title")
    rating = data.get("rating")
    comment = data.get("comment")
    
    if not movie_title or not rating:
        return jsonify({"success": False, "message": "Missing required fields"})
        
    new_review = Review(
        user_id=current_user.id,
        movie_title=movie_title,
        rating=int(rating),
        comment=comment
    )
    db.session.add(new_review)
    db.session.commit()
    
    # Check for new achievements
    newly_earned = check_and_award_achievements(current_user.id)
    
    return jsonify({"success": True, "message": "Review submitted successfully!", "new_achievements": [a.name for a in newly_earned]})

@app.route("/api/watchlist/toggle", methods=["POST"])
@login_required
def toggle_watchlist():
    data = request.get_json()
    title = data.get("title")
    poster = data.get("poster_path")
    tmdb_id = data.get("id")
    
    if not title:
        return jsonify({"success": False, "message": "No title provided"})
        
    existing = Watchlist.query.filter_by(user_id=current_user.id, movie_title=title).first()
    
    if existing:
        db.session.delete(existing)
        action = "removed"
    else:
        new_item = Watchlist(user_id=current_user.id, movie_title=title, poster_path=poster, tmdb_id=tmdb_id)
        db.session.add(new_item)
        action = "added"
        
    db.session.commit()
    
    # Check for new achievements if added
    newly_earned = []
    if action == "added":
        newly_earned = check_and_award_achievements(current_user.id)
    
    return jsonify({"success": True, "action": action, "new_achievements": [a.name for a in newly_earned]})

@app.route("/watchlist")
@login_required
def watchlist_page():
    wl_items = Watchlist.query.filter_by(user_id=current_user.id).all()
    return render_template("watchlist.html", movies=wl_items, user=current_user)

@app.route("/api/watchlist/update-status", methods=["POST"])
@login_required
def update_watchlist_status():
    """Update the watch status of a watchlist item"""
    data = request.get_json()
    movie_title = data.get("title")
    new_status = data.get("status")
    
    valid_statuses = ["want_to_watch", "watching", "watched"]
    if not movie_title or new_status not in valid_statuses:
        return jsonify({"success": False, "message": "Invalid request"}), 400
    
    item = Watchlist.query.filter_by(user_id=current_user.id, movie_title=movie_title).first()
    if not item:
        return jsonify({"success": False, "message": "Not in watchlist"}), 404
    
    item.watch_status = new_status
    db.session.commit()
    return jsonify({"success": True, "status": new_status})

@app.route("/api/achievements")
@login_required
def get_achievements():
    """Get user's achievement progress"""
    progress = get_achievement_progress(current_user.id)
    return jsonify({"achievements": [
        {
            "name": p["achievement"].name,
            "description": p["achievement"].description,
            "icon": p["achievement"].icon,
            "is_earned": p["is_earned"],
            "progress": p["progress"],
            "current": p["current"],
            "required": p["required"]
        } for p in progress
    ]})

@app.route("/lists")
@login_required
def lists_page():
    """View all user's custom movie lists"""
    user_lists = MovieList.query.filter_by(user_id=current_user.id).order_by(MovieList.created_at.desc()).all()
    return render_template("lists.html", lists=user_lists, user=current_user)

@app.route("/api/lists/create", methods=["POST"])
@login_required
def create_list():
    """Create a new movie list"""
    data = request.get_json()
    name = data.get("name")
    description = data.get("description", "")
    is_public = data.get("is_public", True)
    
    if not name:
        return jsonify({"success": False, "message": "List name is required"})
    
    new_list = MovieList(
        user_id=current_user.id,
        name=name,
        description=description,
        is_public=is_public
    )
    db.session.add(new_list)
    db.session.commit()
    
    # Check for achievements
    newly_earned = check_and_award_achievements(current_user.id)
    
    return jsonify({"success": True, "list_id": new_list.id, "new_achievements": [a.name for a in newly_earned]})

@app.route("/api/lists/<int:list_id>/add_movie", methods=["POST"])
@login_required
def add_movie_to_list(list_id):
    """Add a movie to a list"""
    movie_list = MovieList.query.get_or_404(list_id)
    
    # Check ownership
    if movie_list.user_id != current_user.id:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    data = request.get_json()
    movie_title = data.get("movie_title")
    poster_path = data.get("poster_path")
    tmdb_id = data.get("tmdb_id")
    
    # Check if already in list
    existing = ListItem.query.filter_by(list_id=list_id, movie_title=movie_title).first()
    if existing:
        return jsonify({"success": False, "message": "Movie already in list"})
    
    list_item = ListItem(
        list_id=list_id,
        movie_title=movie_title,
        poster_path=poster_path,
        tmdb_id=tmdb_id
    )
    db.session.add(list_item)
    db.session.commit()
    
    return jsonify({"success": True})

@app.route("/api/lists/<int:list_id>/delete", methods=["DELETE"])
@login_required
def delete_list(list_id):
    """Delete a movie list"""
    movie_list = MovieList.query.get_or_404(list_id)
    
    if movie_list.user_id != current_user.id:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    db.session.delete(movie_list)
    db.session.commit()
    
    return jsonify({"success": True})


@app.route("/api/search")
def api_search():
    """Live TMDB movie search for the search modal"""
    query = request.args.get("q", "").strip()
    if not query or len(query) < 2:
        return jsonify({"results": []})
    results = search_movies(query)
    return jsonify({"results": results})


@app.route("/api/trending")
def api_trending():
    """Trending movies from TMDB"""
    time_window = request.args.get("window", "week")
    movies = fetch_trending_movies(time_window)
    return jsonify({"results": movies})


@app.route("/api/watchlist", methods=["GET"])
@login_required
def get_watchlist_json():
    """Return the current user's watchlist as JSON"""
    items = Watchlist.query.filter_by(user_id=current_user.id).order_by(Watchlist.added_at.desc()).all()
    return jsonify({"watchlist": [
        {
            "title": item.movie_title,
            "poster_path": item.poster_path,
            "tmdb_id": item.tmdb_id,
            "added_at": item.added_at.isoformat() if item.added_at else None,
            "watch_status": item.watch_status or "want_to_watch"
        } for item in items
    ]})


# ===== NEW FEATURE 1: Trending Page =====
@app.route("/trending")
def trending_page():
    """Dedicated trending movies page"""
    return render_template("trending.html", user=current_user)


# ===== NEW FEATURE 2: Top Charts Page =====
@app.route("/charts")
def charts_page():
    """Top charts page with genre-based rankings"""
    top_movies = []
    genres = []
    selected_genre = request.args.get("genre", "All")
    
    if not movies_df.empty:
        genres = sorted(movies_df['genre'].dropna().unique().tolist())
        
        df = movies_df.copy()
        if selected_genre and selected_genre != "All":
            df = df[df['genre'].str.contains(selected_genre, na=False)]
        
        # Top by avg_rating with at least some votes
        if 'avg_rating' in df.columns:
            top = df.nlargest(20, 'avg_rating')[['title', 'genre', 'year', 'avg_rating']].to_dict('records')
        else:
            top = df.head(20)[['title', 'genre', 'year']].to_dict('records')
        
        # Enrich with TMDB poster
        for i, m in enumerate(top):
            details = fetch_movie_details(m['title'])
            if details:
                m['poster_path'] = details.get('poster_path', '')
                m['vote_average'] = details.get('vote_average', m.get('avg_rating', 'N/A'))
                m['release_date'] = details.get('release_date', str(m.get('year', '')))
                m['tmdb_id'] = details.get('id')
            else:
                m['poster_path'] = ''
                m['vote_average'] = m.get('avg_rating', 'N/A')
                m['release_date'] = str(m.get('year', ''))
            m['rank'] = i + 1
        top_movies = top
    
    return render_template("charts.html", user=current_user, top_movies=top_movies, genres=genres, selected_genre=selected_genre)


# ===== NEW FEATURE 3: Movie Comparison =====
@app.route("/compare")
def compare_page():
    """Side-by-side movie comparison"""
    title_a = request.args.get("a", "").strip()
    title_b = request.args.get("b", "").strip()
    movie_a = fetch_full_movie_details(title_a) if title_a else None
    movie_b = fetch_full_movie_details(title_b) if title_b else None
    
    movie_list = movies_df[['title']].to_dict('records') if not movies_df.empty else []
    return render_template("compare.html", user=current_user, movie_a=movie_a, movie_b=movie_b,
                           title_a=title_a, title_b=title_b, movie_list=movie_list)


# ===== NEW FEATURE 4: User Stats API =====
@app.route("/api/stats")
@login_required
def api_user_stats():
    """Return rich stats for the current user"""
    reviews = Review.query.filter_by(user_id=current_user.id).all()
    history = ViewingHistory.query.filter_by(user_id=current_user.id).all()
    watchlist_count = Watchlist.query.filter_by(user_id=current_user.id).count()
    watched_count = Watchlist.query.filter_by(user_id=current_user.id, watch_status='watched').count()
    
    # Avg rating given
    avg_rating = round(sum(r.rating for r in reviews) / len(reviews), 1) if reviews else 0
    
    # Unique movies viewed
    unique_movies = len(set(h.movie_title for h in history))
    
    # Top genre from reviews/history movie titles
    all_titles = list(set([r.movie_title for r in reviews] + [h.movie_title for h in history]))
    top_genre = "N/A"
    if all_titles and not movies_df.empty:
        genre_counts = Counter()
        for title in all_titles:
            row = movies_df[movies_df['title'] == title]
            if not row.empty:
                genre = str(row.iloc[0].get('genre', ''))
                for g in genre.split('|'):
                    g = g.strip()
                    if g:
                        genre_counts[g] += 1
        if genre_counts:
            top_genre = genre_counts.most_common(1)[0][0]
    
    return jsonify({
        "movies_viewed": unique_movies,
        "reviews_written": len(reviews),
        "watchlist_count": watchlist_count,
        "watched_count": watched_count,
        "avg_rating_given": avg_rating,
        "top_genre": top_genre,
        "member_since": current_user.created_at.strftime("%b %Y") if current_user.created_at else "N/A"
    })


# ===== NEW FEATURE 5: Personalized "For You" Recommendations =====
@app.route("/api/for-you")
@login_required
def api_for_you():
    """Personalized recommendations based on viewing history"""
    if not hybrid_model:
        return jsonify({"results": []})
    
    history = ViewingHistory.query.filter_by(user_id=current_user.id).order_by(
        ViewingHistory.viewed_at.desc()).limit(10).all()
    reviews = Review.query.filter_by(user_id=current_user.id).order_by(
        Review.created_at.desc()).limit(5).all()
    
    seed_titles = list(set([h.movie_title for h in history] + [r.movie_title for r in reviews]))
    
    if not seed_titles:
        return jsonify({"results": [], "message": "Watch some movies first to get personalized picks!"})
    
    try:
        recs = hybrid_model.recommend(seed_titles[:5], current_user.id, n=6)
        results = []
        for title in recs:
            details = fetch_movie_details(title)
            if details:
                results.append(details)
        return jsonify({"results": results})
    except Exception as e:
        return jsonify({"results": [], "error": str(e)})


# ===== NEW FEATURE 8: Review Likes =====
@app.route("/api/reviews/<int:review_id>/like", methods=["POST"])
@login_required
def toggle_review_like(review_id):
    """Toggle like on a review"""
    review = Review.query.get_or_404(review_id)
    
    existing_like = ReviewLike.query.filter_by(user_id=current_user.id, review_id=review_id).first()
    
    if existing_like:
        db.session.delete(existing_like)
        liked = False
    else:
        new_like = ReviewLike(user_id=current_user.id, review_id=review_id)
        db.session.add(new_like)
        liked = True
    
    db.session.commit()
    return jsonify({"success": True, "liked": liked, "like_count": review.get_like_count()})


@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html", user=current_user), 404


if __name__ == "__main__":
    app.run(debug=True)
