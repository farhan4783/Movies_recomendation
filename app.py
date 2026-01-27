from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import pandas as pd
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
import os

from model.recommenders import PopularityRecommender, ContentBasedRecommender, CollaborativeRecommender, HybridRecommender
from model.ai_recommender import get_ai_recommendation, get_mood_recommendation
from utils.tmdb_client import fetch_movie_details, fetch_popular_movies, fetch_full_movie_details
from model import db
from model.models import User, Watchlist, Review

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "super_secret_key_change_this")

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

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
    hybrid_model = HybridRecommender(content_model, collab_model)
    print("Models Initialized.")
except Exception as e:
    print(f"Error loading models: {e}")
    # Fallback for safe startup if data is missing
    movies_df = pd.DataFrame()
    pop_model = None

@app.route("/", methods=["GET", "POST"])
def index():
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
    genres = sorted(movies_df['genre'].dropna().unique().tolist())
    movie_list = movies_df[['title']].to_dict('records')

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
            login_user(user)
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Invalid username or password')
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user:
             return render_template('register.html', error='Username already exists')
        
        new_user = User(username=username, password=generate_password_hash(password, method='scrypt'))
        db.session.add(new_user)
        db.session.commit()
        
        login_user(new_user)
        return redirect(url_for('index'))
        
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile():
    reviews = Review.query.filter_by(user_id=current_user.id).order_by(Review.created_at.desc()).all()
    watchlist_count = Watchlist.query.filter_by(user_id=current_user.id).count()
    return render_template('profile.html', user=current_user, reviews=reviews, watchlist_count=watchlist_count)

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

@app.route("/movie/<path:title>")
def movie_details(title):
    # Fetch full details
    details = fetch_full_movie_details(title)
    
    if not details:
        # Fallback if not found by title 
        return render_template("index.html", error=f"Movie '{title}' details not found.", user=current_user)

    in_watchlist = False
    if current_user.is_authenticated:
        exists = Watchlist.query.filter_by(user_id=current_user.id, movie_title=details['title']).first()
        if exists:
            in_watchlist = True
            
    reviews = Review.query.filter_by(movie_title=details['title']).order_by(Review.created_at.desc()).all()
            
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
    
    return jsonify({"success": True, "message": "Review submitted successfully!"})

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
    return jsonify({"success": True, "action": action})

@app.route("/watchlist")
@login_required
def watchlist_page():
    wl_items = Watchlist.query.filter_by(user_id=current_user.id).all()
    return render_template("watchlist.html", movies=wl_items, user=current_user)


if __name__ == "__main__":
    app.run(debug=True)
