import pandas as pd
from sklearn.neighbors import NearestNeighbors

# Load datasets
movies = pd.read_csv("data/movies.csv")
ratings = pd.read_csv("data/ratings.csv")

# Create User-Movie Matrix
movie_user_matrix = ratings.pivot_table(
    index='movieId',
    columns='userId',
    values='rating'
).fillna(0)

# Train KNN Model
knn = NearestNeighbors(metric='cosine', algorithm='brute')
knn.fit(movie_user_matrix)

def recommend_movies(movie_title, n_recommendations=3):
    try:
        movie_id = movies[movies['title'] == movie_title]['movieId'].values[0]
        movie_index = movie_user_matrix.index.tolist().index(movie_id)

        distances, indices = knn.kneighbors(
            movie_user_matrix.iloc[movie_index].values.reshape(1, -1),
            n_neighbors=n_recommendations + 1
        )

        recommendations = []
        for i in indices.flatten()[1:]:
            movie_id = movie_user_matrix.index[i]
            title = movies[movies['movieId'] == movie_id]['title'].values[0]
            recommendations.append(title)

        return recommendations
    except (IndexError, ValueError):
        return ["No recommendations available for this movie."]
