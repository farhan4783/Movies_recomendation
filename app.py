from flask import Flask, render_template, request, jsonify
import pandas as pd
from model.recommenders import PopularityRecommender, ContentBasedRecommender, CollaborativeRecommender, HybridRecommender
from model.ai_recommender import get_ai_recommendation
from utils.tmdb_client import fetch_movie_details, fetch_popular_movies

app = Flask(__name__)

# Load Data Globaly
try:
    movies_df = pd.read_csv("data/movies.csv")
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
                # Fallback object
                popular_movies_display.append({
                    "title": title,
                    "poster_path": "https://via.placeholder.com/200x300?text=No+Image",
                    "vote_average": "N/A",
                    "release_date": ""
                })

    if request.method == "POST":
        selected_movie = request.form.get("movie")
        
        try:
            # Use Hybrid Model by default for best results
            # We need a user_id for collaborative filtering. 
            # Since we don't have login, we'll arbitrarily use user_id=1 (or a new user logic)
            # For this demo, let's use user_id=1 as a "proxy" for the current user session
            current_user_id = 1 
            
            # Handle multi-movie selection
            selected_movies_json = request.form.get("selected_movies")
            if selected_movies_json:
                import json
                try:
                    selected_movies = json.loads(selected_movies_json)
                except:
                    selected_movies = [selected_movies_json] # Fallback
            else:
                 # Fallback to single old field
                 val = request.form.get("movie")
                 selected_movies = [val] if val else []

            if not selected_movies:
                 error = "Please select at least one movie."
            else:
                raw_recs = hybrid_model.recommend(selected_movies, current_user_id, n=5)
            
            # Fetch details for recommendations
            for title in raw_recs:
                details = fetch_movie_details(title)
                if details:
                    recommendations.append(details)
                else:
                    recommendations.append({
                        "title": title,
                        "poster_path": "https://via.placeholder.com/200x300?text=No+Image",
                        "vote_average": "N/A",
                        "release_date": ""
                    })
                    
            if not recommendations:
                error = "Could not find recommendations for this movie."
                
        except Exception as e:
            error = f"Error: {str(e)}"
            print(e)

    movie_list = movies_df[['title']].to_dict('records') # For dropdown

    return render_template(
        "index.html",
        movies=movie_list,
        recommendations=recommendations,
        selected_movie=selected_movies if isinstance(selected_movies, list) else selected_movies,
        popular_movies=popular_movies_display,
        error=error
    )

@app.route("/api/chat", methods=["POST"])
def ai_chat():
    data = request.get_json()
    user_query = data.get("query")
    
    if not user_query:
        return jsonify({"response": "Please say something!"})
        
    response = get_ai_recommendation(user_query)
    return jsonify({"response": response})

if __name__ == "__main__":
    app.run(debug=True)
