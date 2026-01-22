import pandas as pd

def manual_enrich():
    print("Loading Data...")
    movies_df = pd.read_csv("data/movies.csv")
    ratings_df = pd.read_csv("data/ratings.csv")

    # 1. Calculate Average Rating
    print("Calculating Ratings...")
    avg_ratings = ratings_df.groupby('movieId')['rating'].mean().round(1)
    movies_df = movies_df.merge(avg_ratings, on='movieId', how='left')
    movies_df.rename(columns={'rating': 'avg_rating'}, inplace=True)
    movies_df['avg_rating'].fillna(0, inplace=True)

    # 2. Hardcoded Years for the specific dataset (titles match movies.csv)
    # This is a fallback since TMDB Key is missing
    year_map = {
        "The Dark Knight": 2008,
        "Inception": 2010,
        "Interstellar": 2014,
        "Avengers": 2012,
        "Titanic": 1997,
        "Notebook": 2004,
        "Pulp Fiction": 1994,
        "The Shawshank Redemption": 1994,
        "Forrest Gump": 1994,
        "The Matrix": 1999,
        "Gladiator": 2000,
        "The Lord of the Rings: The Fellowship of the Ring": 2001,
        "The Godfather": 1972,
        "Schindler's List": 1993,
        "Fight Club": 1999,
        "The Silence of the Lambs": 1991,
        "Star Wars: Episode IV - A New Hope": 1977,
        "The Lion King": 1994,
        "Jurassic Park": 1993,
        "Terminator 2: Judgment Day": 1991,
        "Back to the Future": 1985,
        "The Princess Bride": 1987,
        "Goodfellas": 1990,
        "Casablanca": 1942,
        "Raiders of the Lost Ark": 1981,
        "The Usual Suspects": 1995,
        "Se7en": 1995,
        "Braveheart": 1995,
        "Amélie": 2001,
        "Spirited Away": 2001
    }

    print("applying manual years...")
    # Map title to year, defaulting to 2000 if not found (though all should match)
    movies_df['year'] = movies_df['title'].map(year_map).fillna(2000).astype(int)
    
    # Save enriched data
    movies_df.to_csv("data/movies_enriched.csv", index=False)
    print("Manual Enrichment Complete. Saved to data/movies_enriched.csv")
    print(movies_df.head())

if __name__ == "__main__":
    manual_enrich()
