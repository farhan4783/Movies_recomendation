# Movie Recommendation System

A machine learning-based movie recommendation system using KNN and collaborative filtering. This web application allows users to select a movie they like and receive personalized recommendations based on user ratings and similarity scores.


![alt text](image.png)

![alt text](image-1.png)

![alt text](image-2.png)

## Features
- **Multi-Movie Selection**: Search and select up to 5 movies to get more accurate, hybrid recommendations based on a collective taste profile.
- **AI-Powered Chat Assistant**: "The Point Blank" AI assistant (powered by **Gemini-1.5-Flash**) helps users discover movies through natural language conversation.
- **Hybrid Recommendation Engine**: Combines content-based filtering (genres, keywords) and collaborative filtering (user ratings) for robust suggestions.
- **Modern UI/UX**: A completely overhauled, responsive interface featuring glassmorphism, smooth animations, and a "Point Blank" branded dark theme.
- **Interactive Elements**: Dynamic movie search with autocomplete, chip-based selection, and a sticky chat interface.
- **Modyverse**: mood based movie recommendations.

## Tech Stack
- **Backend**: Python, Flask
- **AI/ML**: 
    - Google Gemini API (LLM for Chat)
    - Scikit-learn (KNN, Cosine Similarity)
    - Pandas, NumPy
- **Frontend**: HTML5, Modern CSS (Glassmorphism, Animations), JavaScript (Vanilla)
- **Data**: CSV datasets for movies and ratings

## Installation and Setup

1. **Clone or Download** the project repository.

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Setup**:
   Create a `.env` file in the root directory and add your Google Gemini API key:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```

4. **Run the Application**:
   ```bash
   python app.py
   ```

5. **Access the App**:
   Open your browser and visit `http://127.0.0.1:5000/`.

## Usage
### getting Recommendations
1. **Search**: Type a movie name in the search bar.
2. **Select**: Click "Add" or press Enter to add it to your selection list (up to 5 movies).
3. **Get Results**: Click "Get Recommendations" to see 5 personalized movie suggestions based on your selection.

### Hybrid AI Chat
- Scroll down onto the **AI Movie Assistant** section.
- Type any request (e.g., "I want a sci-fi movie with a mind-bending plot like Inception").
- The AI will analyze your request and suggest movies with reasons.

## Project Structure
```
movie-recommendation/
├── app.py                 # Main Flask application with hybrid logic
├── model/
│   ├── recommenders.py    # Hybrid, Content, and Collab engines
│   └── ai_recommender.py  # Gemini AI integration
├── templates/
│   └── index.html         # Modern single-page interface
├── static/
│   └── style.css          # Advanced styling & animations
├── data/
│   ├── movies.csv         # Movie dataset
│   └── ratings.csv        # User ratings dataset
├── requirements.txt       # Python dependencies
└── README.md              # This file
```

## Dataset
- **Movies**: Expanded dataset including metadata for content-based filtering.
- **Ratings**: User interaction data for collaborative filtering.

## Future Improvements
- Integrate with TMDB API for real-time posters and metadata.[done].
- User accounts to save watchlists and favorite movies.[done].
- Advanced filtering by year, genre, and rating.[done].


## Key Improvements
1. User Reviews System
What's New: Users can now rate and review movies directly on the Movie Details page.
How it works:
Go to any movie page.
If logged in, you'll see a "Leave a Review" section with a 5-star rating selector.
Submit your review and see it appear instantly in the "User Reviews" list below.
2. Modyverse Fixed & Upgrade
What's New: The "Modyverse" mood-based recommendation engine is now fully functional.
Fix: Connected the frontend questionnaire to a dedicated API endpoint that uses Google Gemini to generate personalized suggestions based on your mood, story preference, and watching company.
3. Enhanced User Profile
What's New: A brand new, stylish Profile Dashboard.
Features:
Avatar: Generates a unique avatar based on your username (using DiceBear API). You can regenerate it with a click!
Bio: Add a personal bio to share your movie taste with the world.
Stats: View your total Watchlist count and Reviews count at a glance.
My Reviews: See a history of all the reviews you've written.
Watchlist: (Existing feature) View your saved movies.


## Visuals (Mockup)
Movie Details with Reviews
The movie page now features a User Reviews section right below the cast list.

Profile Page
Navigate to your profile by clicking your username in the navbar to edit your bio and see your stats.
