import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def get_ai_recommendation(query, movie_context=None):
    """
    Asks Gemini for movie recommendations based on user query.
    movie_context: Optional list of movies the user already liked or is looking at.
    """
    if not GEMINI_API_KEY:
        return "I'm sorry, my brain (API Key) is missing. Please configure the Gemini API Key."

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
