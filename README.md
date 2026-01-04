# Movie Recommendation System

A machine learning-based movie recommendation system using KNN and collaborative filtering. This web application allows users to select a movie they like and receive personalized recommendations based on user ratings and similarity scores.

## Features
- **Collaborative Filtering**: Uses KNN algorithm with cosine similarity to find similar movies based on user ratings.
- **Web Interface**: Clean, responsive Flask web application with modern UI.
- **Error Handling**: Robust error handling for better user experience.
- **Dataset**: Expanded dataset with 30 movies and ratings from 10 users for improved recommendations.

## Tech Stack
- **Backend**: Python, Flask
- **ML**: Pandas, NumPy, Scikit-learn
- **Frontend**: HTML, CSS (responsive design)
- **Data**: CSV files for movies and ratings

## Installation and Setup

1. **Clone or Download** the project repository.

2. **Install Dependencies**:
   ```
   pip install -r requirements.txt
   ```

3. **Run the Application**:
   ```
   python app.py
   ```

4. **Access the App**:
   Open your browser and go to `http://127.0.0.1:5000/` (or the URL shown in the terminal).

## Usage
- Select a movie from the dropdown (movies are displayed with their genres).
- Click "Get Recommendations" to receive 3 similar movie suggestions.
- Recommendations are shown in an attractive card layout.

## Project Structure
```
movie-recommendation/
├── app.py                 # Main Flask application
├── model/
│   └── knn_model.py       # KNN recommendation model
├── templates/
│   └── index.html         # Main web page
├── static/
│   └── style.css          # CSS styles
├── data/
│   ├── movies.csv         # Movie dataset
│   └── ratings.csv        # User ratings dataset
├── requirements.txt       # Python dependencies
└── README.md              # This file
```

## Dataset
- **Movies**: 30 popular movies across various genres (Action, Sci-Fi, Drama, etc.)
- **Ratings**: Simulated ratings from 10 users to demonstrate collaborative filtering

## Future Improvements
- Integrate with real movie databases (e.g., TMDB API) for more movies and posters.
- Add user authentication and personalized profiles.
- Implement content-based filtering for hybrid recommendations.
- Add search functionality and filters by genre.
