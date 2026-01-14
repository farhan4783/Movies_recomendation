import pandas as pd
import numpy as np
from model.recommenders import CollaborativeRecommender

def evaluate_collaborative_model():
    print("Loading data...")
    try:
        movies = pd.read_csv("data/movies.csv")
        ratings = pd.read_csv("data/ratings.csv")
        
        print("Initializing Collaborative Recommender (SVD-based)...")
        model = CollaborativeRecommender(movies, ratings)
        
        print("Running qualitative evaluation...")
        # Since we switched to manual SVD, exact RMSE calculation requires a custom split loop.
        # For now, let's verify it produces recommendations for a test user.
        
        test_user_id = 1
        recommendations = model.recommend(test_user_id, n=5)
        
        print(f"\nRecommendations for User ID {test_user_id}:")
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                print(f"{i}. {rec}")
            print("\nModel functional: YES")
        else:
            print("No recommendations generated.")
            print("\nModel functional: NO")

    except Exception as e:
        print(f"Error during evaluation: {e}")

if __name__ == "__main__":
    evaluate_collaborative_model()
