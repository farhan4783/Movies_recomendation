import pandas as pd
from utils.tmdb_client import fetch_movie_details
import time

def enrich_data():
    print("Loading Data...")
    movies_df = pd.read_csv("data/movies.csv")
    ratings_df = pd.read_csv("data/ratings.csv")

    # 1. Calculate Average Rating
    print("Calculating Ratings...")
    avg_ratings = ratings_df.groupby('movieId')['rating'].mean().round(1)
    movies_df = movies_df.merge(avg_ratings, on='movieId', how='left')
    movies_df.rename(columns={'rating': 'avg_rating'}, inplace=True)
    movies_df['avg_rating'].fillna(0, inplace=True)

    # 2. Fetch Year and Overview from TMDB
    print("Fetching Metadata from TMDB...")
    years = []
    overviews = []
    
    for index, row in movies_df.iterrows():
        print(f"Processing: {row['title']}")
        details = fetch_movie_details(row['title'])
        
        if details and details.get('release_date'):
            year = details['release_date'][:4]
            years.append(year)
        else:
            years.append("N/A")
            
        time.sleep(0.2) # Rate limiting

    movies_df['year'] = years
    
    # Save enriched data
    movies_df.to_csv("data/movies_enriched.csv", index=False)
    print("Enrichment Complete. Saved to data/movies_enriched.csv")
    print(movies_df.head())

if __name__ == "__main__":
    enrich_data()
