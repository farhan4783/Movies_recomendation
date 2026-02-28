"""
Enhanced Recommendation Engine for Movie Maverick
Improvements:
  - ContentBasedRecommender: richer TF-IDF soup with genre boosting,
    sparse-matrix on-demand similarity (avoids full N×N precompute)
  - CollaborativeRecommender: unchanged (SVD-based item-item)
  - HybridRecommender: adaptive weighting + diversity pass
"""
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import TruncatedSVD


class PopularityRecommender:
    def __init__(self, movies_df, ratings_df):
        self.movies_df = movies_df
        self.ratings_df = ratings_df
        self.popularity_df = None
        self._train_model()

    def _train_model(self):
        # Bayesian average weighting: (v/(v+m) * R) + (m/(v+m) * C)
        movie_stats = self.ratings_df.groupby('movieId').agg({'rating': ['count', 'mean']})
        movie_stats.columns = movie_stats.columns.droplevel(0)
        movie_stats = movie_stats.rename(columns={'count': 'vote_count', 'mean': 'vote_average'})

        self.popularity_df = self.movies_df.merge(movie_stats, on='movieId', how='left')

        C = self.popularity_df['vote_average'].mean()
        m = self.popularity_df['vote_count'].quantile(0.9)

        qualified = self.popularity_df.copy().loc[self.popularity_df['vote_count'] >= m]

        def weighted_rating(x, m=m, C=C):
            v = x['vote_count']
            R = x['vote_average']
            return (v / (v + m) * R) + (m / (v + m) * C)

        qualified['score'] = qualified.apply(weighted_rating, axis=1)
        self.popularity_df = qualified.sort_values('score', ascending=False)

    def recommend(self, n=10):
        if self.popularity_df is None or self.popularity_df.empty:
            return []
        return self.popularity_df['title'].head(n).tolist()


class ContentBasedRecommender:
    """
    Improved content-based filtering:
    - Genre repeated 3× in the soup to weight it more heavily
    - Keywords column used if present in the dataframe
    - Sparse TF-IDF matrix kept instead of dense N×N cosine matrix
      (on-demand cosine similarity computation for the query)
    - min_df=2, max_features=15000 to reduce noise
    """

    def __init__(self, movies_df):
        self.movies_df = movies_df.copy().reset_index(drop=True)
        self.indices = None
        self.tfidf_matrix = None
        self.tfidf = None
        self._train_model()

    def _build_soup(self, row):
        parts = []

        # Overview — base signal
        if 'overview' in row.index and pd.notna(row['overview']):
            parts.append(str(row['overview']))

        # Genres — repeated 3× for higher weight
        genre_col = None
        for col in ('genres', 'genre'):
            if col in row.index and pd.notna(row[col]) and str(row[col]).strip():
                genre_col = col
                break
        if genre_col:
            genre_str = str(row[genre_col]).replace('|', ' ').replace(',', ' ')
            parts.extend([genre_str] * 3)  # triple weight

        # Keywords (optional enrichment)
        if 'keywords' in row.index and pd.notna(row['keywords']):
            parts.append(str(row['keywords']).replace('|', ' ').replace(',', ' '))

        # Director (optional enrichment)
        if 'director' in row.index and pd.notna(row['director']):
            parts.append(str(row['director']))

        return ' '.join(parts).strip()

    def _train_model(self):
        self.movies_df['content_soup'] = self.movies_df.apply(self._build_soup, axis=1)

        # Fallback when everything is empty
        if self.movies_df['content_soup'].str.strip().eq('').all():
            self.movies_df['content_soup'] = 'movie'

        self.tfidf = TfidfVectorizer(
            stop_words='english',
            min_df=2,
            max_features=15000,
            ngram_range=(1, 2),
        )
        self.tfidf_matrix = self.tfidf.fit_transform(self.movies_df['content_soup'])

        # Title → row index mapping (keep sparse matrix, not dense N×N)
        self.indices = pd.Series(
            self.movies_df.index, index=self.movies_df['title']
        ).drop_duplicates()

    def recommend(self, titles, n=10):
        if isinstance(titles, str):
            titles = [titles]

        valid_indices = []
        for t in titles:
            if t in self.indices:
                idx = self.indices[t]
                if isinstance(idx, pd.Series):
                    idx = idx.iloc[0]
                valid_indices.append(int(idx))

        if not valid_indices:
            return []

        # Build a query vector = mean of the seed movie TF-IDF vectors
        query_vec = self.tfidf_matrix[valid_indices].mean(axis=0)
        # cosine_similarity expects 2-D; np.matrix.mean returns np.matrix
        query_vec = np.asarray(query_vec)  # shape (1, n_features)

        sim_scores = cosine_similarity(query_vec, self.tfidf_matrix)[0]

        # Rank candidates (exclude input movies)
        scored = sorted(
            ((i, float(s)) for i, s in enumerate(sim_scores) if i not in valid_indices),
            key=lambda x: x[1],
            reverse=True,
        )

        top_indices = [i for i, _ in scored[:n]]
        return self.movies_df['title'].iloc[top_indices].tolist()


class CollaborativeRecommender:
    def __init__(self, movies_df, ratings_df):
        self.movies_df = movies_df
        self.ratings_df = ratings_df
        self.movie_user_matrix = None
        self.svd = None
        self.corr_matrix = None
        self._train_model()

    def _train_model(self):
        self.movie_user_matrix = self.ratings_df.pivot_table(
            index='movieId', columns='userId', values='rating'
        ).fillna(0)

        X = self.movie_user_matrix.values
        n_components = min(20, X.shape[1] - 1)

        self.svd = TruncatedSVD(n_components=n_components, random_state=42)
        matrix_reduced = self.svd.fit_transform(X)

        self.corr_matrix = np.corrcoef(matrix_reduced)

    def recommend(self, user_id, n=10):
        user_ratings = self.ratings_df[self.ratings_df['userId'] == user_id]
        if user_ratings.empty:
            return []

        high_rated = user_ratings[user_ratings['rating'] >= 4]['movieId'].tolist()
        if not high_rated:
            high_rated = user_ratings['movieId'].tolist()

        similar_scores = {}
        movie_ids = self.movie_user_matrix.index.tolist()

        for movie_id in high_rated:
            if movie_id in movie_ids:
                idx = movie_ids.index(movie_id)
                corr_vec = self.corr_matrix[idx]
                for i, score in enumerate(corr_vec):
                    target_id = movie_ids[i]
                    if target_id not in high_rated:
                        similar_scores[target_id] = similar_scores.get(target_id, 0) + score

        sorted_scores = sorted(similar_scores.items(), key=lambda x: x[1], reverse=True)
        top_ids = [x[0] for x in sorted_scores[:n]]

        return self.movies_df[self.movies_df['movieId'].isin(top_ids)]['title'].tolist()


class HybridRecommender:
    """
    Weighted hybrid recommender with:
    - Adaptive weights based on user rating history richness
    - Diversity pass: gently penalise genre over-concentration
    """

    def __init__(self, content_model, collaborative_model, popularity_model):
        self.content_model = content_model
        self.collab_model = collaborative_model
        self.pop_model = popularity_model

    def _get_genre(self, title, movies_df):
        """Return genre string for a title, or empty string."""
        rows = movies_df[movies_df['title'] == title]
        if rows.empty:
            return ''
        row = rows.iloc[0]
        for col in ('genres', 'genre'):
            if col in row.index and pd.notna(row[col]):
                return str(row[col])
        return ''

    def recommend(self, titles, user_id, n=10, movies_df=None):
        """
        Adaptive Weighted Hybrid:
          - If user has >= 10 rated movies  → content 1.2, collab 1.4, pop 0.3
          - If user has 1-9 rated movies    → content 1.4, collab 0.8, pop 0.4
          - If user is anonymous/0 ratings  → content 1.5, collab 0.0, pop 0.6
        After ranking, run a diversity pass to avoid genre monotony.
        """
        pool = n * 3  # larger candidate pool for better re-ranking

        # ------ Adaptive weights ------
        try:
            from utils.tmdb_client import _simple_cache  # just used as a flag
        except Exception:
            pass

        user_rating_count = 0
        try:
            # Import here to avoid circular deps at module load time
            from model.models import Review
            from model import db
            # This may not work in offline/test contexts — wrap safely
            user_rating_count = Review.query.filter_by(user_id=user_id).count()
        except Exception:
            pass

        if user_rating_count >= 10:
            w_content, w_collab, w_pop = 1.2, 1.4, 0.3
        elif user_rating_count >= 1:
            w_content, w_collab, w_pop = 1.4, 0.8, 0.4
        else:
            w_content, w_collab, w_pop = 1.5, 0.0, 0.6

        # ------ Gather recommendations ------
        content_recs = self.content_model.recommend(titles, n=pool) if w_content > 0 else []
        collab_recs = self.collab_model.recommend(user_id, n=pool) if w_collab > 0 else []
        pop_recs = self.pop_model.recommend(n=pool) if w_pop > 0 else []

        all_candidates = {}

        def rrf_score(recs, weight):
            """Reciprocal Rank Fusion scoring with weight."""
            for i, title in enumerate(recs):
                score = weight / (i + 1)
                all_candidates[title] = all_candidates.get(title, 0) + score

        rrf_score(content_recs, w_content)
        rrf_score(collab_recs, w_collab)
        rrf_score(pop_recs, w_pop)

        # ------ Sort ------
        sorted_candidates = sorted(all_candidates.items(), key=lambda x: x[1], reverse=True)

        input_set = set(titles) if isinstance(titles, list) else {titles}

        # ------ Diversity pass ------
        # Track genre counts; penalise when a genre exceeds n//2 slots
        results = []
        genre_counts = {}

        for title, score in sorted_candidates:
            if title in input_set:
                continue

            if movies_df is not None:
                genre = self._get_genre(title, movies_df)
                primary_genre = genre.split('|')[0].split(',')[0].strip() if genre else ''
                count = genre_counts.get(primary_genre, 0)
                if primary_genre and count >= max(2, n // 2):
                    continue  # skip this one to improve diversity
                genre_counts[primary_genre] = count + 1

            results.append(title)
            if len(results) >= n:
                break

        # Fallback: if diversity pass removed too many, fill from sorted_candidates
        if len(results) < n:
            for title, _ in sorted_candidates:
                if title not in input_set and title not in results:
                    results.append(title)
                    if len(results) >= n:
                        break

        return results
