"""
Enhanced Recommendation Engine for Movie Maverick
Improvements:
  - ContentBasedRecommender: richer TF-IDF soup with genre boosting,
    cast boost (top actors repeated 2×), sparse-matrix on-demand similarity
  - CollaborativeRecommender: SVD-based item-item
  - HybridRecommender: adaptive weighting + diversity pass + temporal decay
    + serendipity mode + reason tags per recommendation
"""
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import TruncatedSVD
from datetime import datetime

CURRENT_YEAR = datetime.now().year


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

    def recommend(self, n=10, exclude_genres=None):
        """Returns (title, year_or_None) tuples to support temporal decay upstream."""
        if self.popularity_df is None or self.popularity_df.empty:
            return []
        df = self.popularity_df.copy()
        if exclude_genres:
            # Filter out entries whose primary genre matches any in exclude_genres
            def _genre_excluded(row):
                g = str(row.get('genre', '') or row.get('genres', '')).split('|')[0].split(',')[0].strip()
                return g.lower() in {eg.lower() for eg in exclude_genres}
            mask = df.apply(_genre_excluded, axis=1)
            df = df[~mask]
        return df['title'].head(n).tolist()


class ContentBasedRecommender:
    """
    Improved content-based filtering:
    - Genre repeated 3× in the soup to weight it more heavily
    - Top cast members repeated 2× (if 'cast' column present)
    - Keywords column used if present in the dataframe
    - Director repeated 2× if present
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

        # Director — repeated 2× for stronger signal
        if 'director' in row.index and pd.notna(row['director']):
            director_str = str(row['director']).replace(' ', '_')
            parts.extend([director_str] * 2)

        # Cast — top 3 actors, repeated 2×
        if 'cast' in row.index and pd.notna(row['cast']):
            cast_str = str(row['cast'])
            # Support pipe-separated or comma-separated
            actors = [a.strip().replace(' ', '_') for a in cast_str.replace('|', ',').split(',')][:3]
            cast_part = ' '.join(actors)
            parts.extend([cast_part] * 2)

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


def _temporal_boost(title, movies_df):
    """
    Returns a small multiplicative boost [1.0, 1.15] based on movie recency.
    Films from 2010+ get up to +15% boost, older films get 1.0.
    """
    if movies_df is None or movies_df.empty:
        return 1.0
    rows = movies_df[movies_df['title'] == title]
    if rows.empty:
        return 1.0
    try:
        year_col = 'year' if 'year' in rows.columns else None
        if year_col is None:
            return 1.0
        year = int(rows.iloc[0][year_col])
        if year < 1990:
            return 1.0
        # Sigmoid-like linear scale: 1990→1.0, 2025→1.15
        boost = 1.0 + min(0.15, max(0.0, (year - 1990) / (CURRENT_YEAR - 1990) * 0.15))
        return boost
    except Exception:
        return 1.0


class HybridRecommender:
    """
    Weighted hybrid recommender with:
    - Adaptive weights based on user rating history richness
    - Temporal decay: newer movies get a small score boost
    - Diversity pass: gently penalise genre over-concentration
    - Serendipity mode: injects 1-2 out-of-genre discovery picks
    - Reason tags: each recommendation comes with a source label
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

    def recommend(self, titles, user_id, n=10, movies_df=None, with_reasons=False):
        """
        Adaptive Weighted Hybrid with Temporal Decay + Serendipity + Reason Tags.

        Args:
            titles: list of seed movie titles
            user_id: current user ID
            n: number of recommendations to return
            movies_df: DataFrame with movie metadata
            with_reasons: if True, returns list of (title, reason_tag) tuples

        Returns:
            List of title strings (default) or list of (title, reason) tuples.
        """
        pool = n * 4  # larger candidate pool for better re-ranking

        # ------ Adaptive weights ------
        user_rating_count = 0
        try:
            from model.models import Review
            from model import db
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

        # Track which pool each title came from for reason tagging
        content_set = set(content_recs)
        collab_set = set(collab_recs)
        pop_set = set(pop_recs)

        all_candidates = {}
        source_scores = {}

        def rrf_score(recs, weight, source_name):
            for i, title in enumerate(recs):
                score = weight / (i + 1)
                all_candidates[title] = all_candidates.get(title, 0) + score
                if title not in source_scores:
                    source_scores[title] = {}
                source_scores[title][source_name] = source_scores[title].get(source_name, 0) + score

        rrf_score(content_recs, w_content, 'content')
        rrf_score(collab_recs, w_collab, 'collab')
        rrf_score(pop_recs, w_pop, 'popular')

        # ------ Apply temporal decay boost ------
        if movies_df is not None and not movies_df.empty:
            for title in all_candidates:
                boost = _temporal_boost(title, movies_df)
                all_candidates[title] *= boost

        # ------ Sort ------
        sorted_candidates = sorted(all_candidates.items(), key=lambda x: x[1], reverse=True)

        input_set = set(titles) if isinstance(titles, list) else {titles}

        # ------ Diversity pass ------
        results = []
        reasons = []
        genre_counts = {}

        for title, score in sorted_candidates:
            if title in input_set:
                continue

            if movies_df is not None:
                genre = self._get_genre(title, movies_df)
                primary_genre = genre.split('|')[0].split(',')[0].strip() if genre else ''
                count = genre_counts.get(primary_genre, 0)
                if primary_genre and count >= max(2, n // 2):
                    continue  # skip for diversity
                genre_counts[primary_genre] = count + 1

            # Determine reason tag
            scores = source_scores.get(title, {})
            top_source = max(scores, key=scores.get) if scores else 'popular'
            reason_map = {
                'content': 'content',
                'collab': 'collab',
                'popular': 'popular',
            }
            reason = reason_map.get(top_source, 'popular')

            results.append(title)
            reasons.append(reason)

            if len(results) >= n:
                break

        # Fallback: if diversity pass removed too many, fill from sorted_candidates
        if len(results) < n:
            for title, _ in sorted_candidates:
                if title not in input_set and title not in results:
                    scores = source_scores.get(title, {})
                    top_source = max(scores, key=scores.get) if scores else 'popular'
                    results.append(title)
                    reasons.append(top_source)
                    if len(results) >= n:
                        break

        # ------ Serendipity Mode ------
        # Inject 1-2 discovery picks from outside the dominant genre(s)
        if movies_df is not None and len(results) >= 3:
            # Determine dominant genres in results
            dominant_genres = set()
            for title in results[:min(5, len(results))]:
                g = self._get_genre(title, movies_df)
                pg = g.split('|')[0].split(',')[0].strip() if g else ''
                if pg:
                    dominant_genres.add(pg)

            # Look for serendipity candidates from popularity pool (outside dominant)
            serendipity_candidates = self.pop_model.recommend(n=20, exclude_genres=dominant_genres)
            serendipity_picks = [t for t in serendipity_candidates
                                 if t not in input_set and t not in results][:2]

            if serendipity_picks:
                # Replace last 1-2 entries with serendipity picks
                num_inject = min(len(serendipity_picks), max(1, n // 6))
                for i in range(num_inject):
                    if len(results) > num_inject:
                        results[-(i + 1)] = serendipity_picks[i]
                        reasons[-(i + 1)] = 'serendipity'

        if with_reasons:
            return list(zip(results, reasons))
        return results
