import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
from sklearn.decomposition import TruncatedSVD

class PopularityRecommender:
    def __init__(self, movies_df, ratings_df):
        self.movies_df = movies_df
        self.ratings_df = ratings_df
        self.popularity_df = None
        self._train_model()

    def _train_model(self):
        # Calculate popularity based on average rating and vote count
        # Simple weighted rating formula: (v/(v+m) * R) + (m/(v+m) * C)
        # v = number of votes for the movie
        # m = minimum votes required to be listed
        # R = average rating of the movie
        # C = mean vote across the whole report
        
        # Merge ratings with movies to get vote counts and averages if not present in movies_df
        # Assuming movies_df might have 'vote_average' and 'vote_count', but let's calculate from ratings_df for freshness
        # Or if ratings_df is just user-item, we aggregate.
        
        # Group by movieId to get count and mean
        movie_stats = self.ratings_df.groupby('movieId').agg({'rating': ['count', 'mean']})
        movie_stats.columns = movie_stats.columns.droplevel(0)
        movie_stats = movie_stats.rename(columns={'count': 'vote_count', 'mean': 'vote_average'})
        
        # Merge with movie titles
        self.popularity_df = self.movies_df.merge(movie_stats, on='movieId', how='left')
        
        C = self.popularity_df['vote_average'].mean()
        m = self.popularity_df['vote_count'].quantile(0.9) # Top 10% valid movies
        
        # Filter movies that qualify for the chart
        qualified_movies = self.popularity_df.copy().loc[self.popularity_df['vote_count'] >= m]
        
        def weighted_rating(x, m=m, C=C):
            v = x['vote_count']
            R = x['vote_average']
            return (v/(v+m) * R) + (m/(v+m) * C)
            
        qualified_movies['score'] = qualified_movies.apply(weighted_rating, axis=1)
        
        # Sort based on score
        self.popularity_df = qualified_movies.sort_values('score', ascending=False)

    def recommend(self, n=10):
        if self.popularity_df is None or self.popularity_df.empty:
            return []
        return self.popularity_df['title'].head(n).tolist()

class ContentBasedRecommender:
    def __init__(self, movies_df):
        self.movies_df = movies_df.copy()
        self.indices = None
        self.cosine_sim = None
        self._train_model()
        
    def _train_model(self):
        # Create a soup of tags (genres + overview + potentially others)
        
        # Check for 'genre' vs 'genres'
        genre_col = 'genres' if 'genres' in self.movies_df.columns else 'genre' if 'genre' in self.movies_df.columns else None
        overview_col = 'overview' if 'overview' in self.movies_df.columns else None

        # Fill NA
        if overview_col:
            self.movies_df[overview_col] = self.movies_df[overview_col].fillna('')
        if genre_col:
            self.movies_df[genre_col] = self.movies_df[genre_col].fillna('')
        
        # Simple content soup: Overview + Genres
        soup_parts = []
        if overview_col:
            soup_parts.append(self.movies_df[overview_col])
        if genre_col:
            soup_parts.append(self.movies_df[genre_col])
            
        if not soup_parts:
            # Fallback if no content
            self.movies_df['content_soup'] = ""
        else:
             # Combine parts
            if len(soup_parts) == 1:
                self.movies_df['content_soup'] = soup_parts[0].astype(str)
            else:
                 self.movies_df['content_soup'] = soup_parts[0].astype(str) + ' ' + soup_parts[1].astype(str)
        
        tfidf = TfidfVectorizer(stop_words='english')
        # Handle empty content
        if self.movies_df['content_soup'].str.strip().eq('').all():
             # If completely empty, identity matrix or skipped
             # Just create a dummy matrix to avoid crash
             tfidf_matrix = tfidf.fit_transform(['a'] * len(self.movies_df)) # Dummy
        else:
            tfidf_matrix = tfidf.fit_transform(self.movies_df['content_soup'])
        
        self.cosine_sim = linear_kernel(tfidf_matrix, tfidf_matrix)
        
        # Mapping from title to index
        self.indices = pd.Series(self.movies_df.index, index=self.movies_df['title']).drop_duplicates()

    def recommend(self, titles, n=10):
        # Convert single title to list if needed
        if isinstance(titles, str):
            titles = [titles]
            
        # Get indices for all valid titles
        valid_indices = []
        for t in titles:
            if t in self.indices:
                idx = self.indices[t]
                if isinstance(idx, pd.Series):
                    idx = idx.iloc[0]
                valid_indices.append(idx)
                
        if not valid_indices:
            return []
            
        # Calculate average vector (user profile)
        user_profile = self.cosine_sim[valid_indices].mean(axis=0)
        
        # Calculate similarity scores against average vector
        # self.cosine_sim is N x N. We need similarity of all movies to this profile.
        # But wait, self.cosine_sim is already computed pair-wise.
        # If we have the raw TF-IDF matrix, we could compute cosine against that.
        # But we only kept cosine_sim (N x N) to save memory/compute (?) actually it's larger.
        # If we only have cosine_sim:
        # Similarity of Movie X to Profile = Mean(Similarity(Movie X, Movie 1), Similarity(Movie X, Movie 2)...)
        # So we can just take the mean of the rows corresponding to valid_indices per column.
        
        sim_scores = list(enumerate(user_profile))
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
        
        # Get top n (excluding the input movies themselves)
        # Filter out input indices
        final_indices = []
        for i, score in sim_scores:
            if i not in valid_indices:
                final_indices.append(i)
                if len(final_indices) >= n:
                    break
        
        return self.movies_df['title'].iloc[final_indices].tolist()

class CollaborativeRecommender:
    def __init__(self, movies_df, ratings_df):
        self.movies_df = movies_df
        self.ratings_df = ratings_df
        self.movie_user_matrix = None
        self.svd = None
        self.corr_matrix = None
        self._train_model()

    def _train_model(self):
        # Create Pivot Table (Movie vs User)
        self.movie_user_matrix = self.ratings_df.pivot_table(index='movieId', columns='userId', values='rating').fillna(0)
        
        # Transpose to (User vs Movie) for SVD if we wanted User embeddings, 
        # but for Item-Item similarity, we can stick to Movie-User or just use the matrix directly.
        # Let's use TruncatedSVD to reduce dimensions of the Pivot Matrix
        X = self.movie_user_matrix.values
        
        # We need to handle the case where we have small data
        n_components = min(20, X.shape[1]-1) 
        
        self.svd = TruncatedSVD(n_components=n_components, random_state=42)
        matrix_reduced = self.svd.fit_transform(X)
        
        # Calculate correlation matrix using numpy's corrcoef on the reduced matrix
        self.corr_matrix = np.corrcoef(matrix_reduced)

    def recommend(self, user_id, n=10):
        # Since we switched to Item-Item similarity via SVD (simplified for this demo without surprise),
        # A purely collaborative user-based prediction is complex to hand-roll perfectly without a lib.
        # Instead, we will implement an "Item-based Collaborative Filtering" approach.
        # We look at movies the user has rated highly, and find similar movies in the latent space.
        
        user_ratings = self.ratings_df[self.ratings_df['userId'] == user_id]
        if user_ratings.empty:
            return []

        # Get high rated movies by this user
        high_rated_movies = user_ratings[user_ratings['rating'] >= 4]['movieId'].tolist()
        
        if not high_rated_movies:
            high_rated_movies = user_ratings['movieId'].tolist() # Fallback to any watched

        similar_movies_scores = {}

        movie_ids = self.movie_user_matrix.index.tolist()
        
        for movie_id in high_rated_movies:
            if movie_id in movie_ids:
                idx = movie_ids.index(movie_id)
                correlation_vector = self.corr_matrix[idx]
                
                # Get top correlated movies
                # We simply add up correlations for candidate movies
                for i, score in enumerate(correlation_vector):
                    target_id = movie_ids[i]
                    if target_id not in high_rated_movies: # Don't recommend what is already seen w/ high rating
                        if target_id not in similar_movies_scores:
                            similar_movies_scores[target_id] = 0
                        similar_movies_scores[target_id] += score
        
        # Sort by score
        sorted_scores = sorted(similar_movies_scores.items(), key=lambda x: x[1], reverse=True)
        top_movie_ids = [x[0] for x in sorted_scores[:n]]
        
        return self.movies_df[self.movies_df['movieId'].isin(top_movie_ids)]['title'].tolist()

class HybridRecommender:
    def __init__(self, content_model, collaborative_model, popularity_model):
        self.content_model = content_model
        self.collab_model = collaborative_model
        self.pop_model = popularity_model

    def recommend(self, titles, user_id, n=10):
        """
        A scientific weighted hybrid approach:
        - Content Similarity: 40%
        - Collaborative Signal: 40%
        - Popularity/Quality: 20%
        """
        # 1. Get recommendations from sub-models with their scores if possible
        # Since our sub-models currently return titles, we'll assign rank-based scores
        
        content_recs = self.content_model.recommend(titles, n=n*2)
        collab_recs = self.collab_model.recommend(user_id, n=n*2)
        pop_recs = self.pop_model.recommend(n=n*2)
        
        all_candidates = {}
        
        # Rank-based scoring (Reciprocal Rank Fusion or weighted rank)
        def add_scores(recs, weight):
            for i, title in enumerate(recs):
                score = (1.0 / (i + 1)) * weight
                all_candidates[title] = all_candidates.get(title, 0) + score
                
        add_scores(content_recs, 1.2) # Content is highly relevant to recent taste
        add_scores(collab_recs, 1.0)  # Collab helps with discovery
        add_scores(pop_recs, 0.4)     # Popularity adds "safe" recommendations
        
        # 2. Sort candidates by final score
        sorted_candidates = sorted(all_candidates.items(), key=lambda x: x[1], reverse=True)
        
        # 3. Filter and return top n
        # Exclude movies the user has already provided in 'titles'
        input_titles = set(titles) if isinstance(titles, list) else {titles}
        
        hybrid = []
        for title, score in sorted_candidates:
            if title not in input_titles:
                hybrid.append(title)
                if len(hybrid) >= n:
                    break
                    
        return hybrid
