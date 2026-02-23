try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except (ImportError, AttributeError, Exception) as e:
    print(f"Warning: Failed to import google.generativeai: {e}")
    genai = None
    GENAI_AVAILABLE = False
import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY and GENAI_AVAILABLE:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"Error configuring Gemini: {e}")
        GENAI_AVAILABLE = False

def get_ai_recommendation(query, movie_context=None):
    """
    Asks Gemini for movie recommendations based on user query.
    movie_context: Optional list of movies the user already liked or is looking at.
    """
    if not GEMINI_API_KEY or not GENAI_AVAILABLE:
        return "I'm sorry, I cannot think right now (AI library or key missing)."

    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        prompt = f"""
        You are an expert movie critic and recommender system.
        
        User Query: "{query}"
        
        Context: The user is using a movie recommendation app.
        
        Please suggest 3-5 movies that match the user's request. 
        For each movie, provide a very brief reason (1 sentence) why it fits.
        Keep the tone friendly and enthusiastic.
        Format the output as a simple list or paragraph.
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return "I'm having trouble thinking right now. Please try again later."

def get_mood_recommendation(answers):
    """
    answers: dict containing 'mood', 'story_type', 'company'
    """
    if not GEMINI_API_KEY or not GENAI_AVAILABLE:
         return "API Key or Library missing."

    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        prompt = f"""
        You are a sophisticated movie curator. The user has answered some questions about their current state:
        
        1. Mood: {answers.get('mood')}
        2. Story Type: {answers.get('story_type')}
        3. Watching with: {answers.get('company')}
        
        Based on this, suggest 3 perfect movies.
        
        Structure your response exactly like this (return valid HTML structure inside the validation):
        <div class="recommendation-list">
            <div class="rec-item">
                <h3>Movie Title (Year)</h3>
                <p>Why it fits: One sentence explanation.</p>
            </div>
            ...
        </div>
        
        Do not include markdown ticks (```html), just the raw HTML snippet.
        """
        
        response = model.generate_content(prompt)
        text = response.text.replace("```html", "").replace("```", "")
        return text
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return "<p>Sorry, I couldn't generate recommendations right now.</p>"


def get_user_personality(movie_history):
    """
    Analyzes a list of movie titles to generate a 'Movie Personality'.
    movie_history: List of movie titles the user has viewed or reviewed.
    """
    if not GEMINI_API_KEY or not GENAI_AVAILABLE:
        return {
            "title": "The Mysterious Viewer",
            "description": "We need more data (and an API key) to reveal your true cinematic soul.",
            "traits": ["Enigmatic", "Private", "Unpredictable"]
        }

    if not movie_history:
        return {
            "title": "The Blank Canvas",
            "description": "You haven't watched enough movies for me to analyze your personality yet. Start exploring!",
            "traits": ["Open-minded", "Newbie", "Curious"]
        }

    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        movies_str = ", ".join(movie_history[:20]) # Limit to top 20 for prompt size
        
        prompt = f"""
        Analyze the following list of movies watched by a user and determine their "Movie Personality".
        
        Movies: {movies_str}
        
        Provide the result in the following JSON format:
        {{
            "title": "A creative and catchy personality title (e.g., The Sci-Fi Visionary, The Hopeless Romantic Noir)",
            "description": "A 2-3 sentence fun and insightful description of their cinematic taste.",
            "traits": ["Trait 1", "Trait 2", "Trait 3"]
        }}
        
        Be creative, witty, and slightly hyperbolic. Ensure the response is ONLY the JSON object.
        """
        
        response = model.generate_content(prompt)
        import json
        
        # Clean response text in case Gemini adds markdown
        text = response.text.replace("```json", "").replace("```", "").strip()
        personality = json.loads(text)
        return personality
        
    except Exception as e:
        print(f"Gemini Personality Error: {e}")
        return {
            "title": "The Indie Enthusiast",
            "description": "You have a diverse taste that defies simple categorization. You're always looking for the next hidden gem.",
            "traits": ["Diverse", "Eclectic", "Unconventional"]
        }
