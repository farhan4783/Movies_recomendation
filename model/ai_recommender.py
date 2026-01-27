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

