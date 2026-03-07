try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except (ImportError, AttributeError, Exception) as e:
    print(f"Warning: Failed to import google.generativeai: {e}")
    genai = None
    GENAI_AVAILABLE = False
import os
import json
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY and GENAI_AVAILABLE:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"Error configuring Gemini: {e}")
        GENAI_AVAILABLE = False

def get_ai_recommendation(query, movie_context=None, preferred_genres=None, recent_movies=None):
    """
    Asks Gemini for movie recommendations based on user query.

    Args:
        query: The user's natural language request.
        movie_context: Optional list of movie titles the user already liked.
        preferred_genres: Optional list of genre strings from UserPreferences.
        recent_movies: Optional list of recently watched movie titles (last 5).
    """
    if not GEMINI_API_KEY or not GENAI_AVAILABLE:
        return "I'm sorry, I cannot think right now (AI library or key missing)."

    try:
        model = genai.GenerativeModel('gemini-2.0-flash')

        context_lines = []
        if movie_context:
            context_lines.append(f"Movies the user loves: {', '.join(movie_context[:8])}")
        if recent_movies:
            context_lines.append(f"Recently watched: {', '.join(recent_movies[:5])}")
        if preferred_genres:
            context_lines.append(f"Preferred genres: {', '.join(preferred_genres)}")

        context_block = "\n".join(context_lines) if context_lines else "No prior context available."

        prompt = f"""You are an elite movie critic and passionate recommender with encyclopedic knowledge of cinema.

User Query: "{query}"

User Context:
{context_block}

Task: Suggest 4-5 movies that perfectly match this request. Consider the user's taste profile above.

For each movie provide:
- The movie title and year
- One compelling sentence on why it fits this exact query
- A genre badge (e.g. [Sci-Fi] [Thriller])

Keep the tone warm, enthusiastic, and cinephile-friendly. Use markdown bold for movie titles.
Avoid generic recommendations — dig into the catalogue for hidden gems and acclaimed classics alike."""

        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return "I'm having trouble thinking right now. Please try again later."


def get_mood_recommendation(answers):
    """
    answers: dict containing 'mood', 'story_type', 'company', optionally 'time_of_day'
    Returns an HTML snippet with movie recommendations.
    """
    if not GEMINI_API_KEY or not GENAI_AVAILABLE:
         return "<p>API Key or Library missing.</p>"

    try:
        model = genai.GenerativeModel('gemini-2.0-flash')

        time_of_day = answers.get('time_of_day', 'evening')

        prompt = f"""You are a sophisticated movie curator with exceptional taste. A user has answered questions about their current state:

1. Mood: {answers.get('mood')}
2. Story Type: {answers.get('story_type')}
3. Watching with: {answers.get('company')}
4. Time of Day: {time_of_day}

Based on ALL of these factors together, curate 3 perfect movie picks. Make them diverse yet all fitting.

Structure your response EXACTLY like this (return valid HTML only, no markdown code fences):
<div class="recommendation-list">
    <div class="rec-item">
        <h3>Movie Title (Year)</h3>
        <p class="rec-fit">Why it fits: One compelling sentence that references their specific mood/company/time.</p>
        <p class="rec-genre"><span class="genre-tag">Genre</span></p>
    </div>
    ...
</div>

Make the "Why it fits" sentences genuinely insightful — reference specific elements of what they told you."""

        response = model.generate_content(prompt)
        text = response.text.replace("```html", "").replace("```", "").strip()
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

        movies_str = ", ".join(movie_history[:20])  # Limit to top 20 for prompt size

        prompt = f"""You are an insightful film psychologist. Analyze the viewing history below and determine the user's "Movie Personality".

Movies watched: {movies_str}

Provide the result in the following JSON format:
{{
    "title": "A creative and catchy personality title (e.g., The Sci-Fi Visionary, The Hopeless Romantic Noir)",
    "description": "A 2-3 sentence fun and insightful description of their cinematic taste. Be specific about patterns you notice.",
    "traits": ["Trait 1", "Trait 2", "Trait 3"]
}}

Be creative, witty, and slightly hyperbolic. Look for genre patterns, decade preferences, director affinities.
Ensure the response is ONLY the JSON object, no other text."""

        response = model.generate_content(prompt)

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


def get_ai_similar_explanation(movie_title, similar_titles):
    """
    Get a brief AI explanation for why a set of movies is similar to the seed movie.
    Returns a dict mapping title -> one-sentence reason.
    """
    if not GEMINI_API_KEY or not GENAI_AVAILABLE or not similar_titles:
        return {}

    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        titles_list = "\n".join(f"- {t}" for t in similar_titles[:6])

        prompt = f"""For the movie "{movie_title}", explain in ONE short sentence (max 12 words) why each of these movies is similar:

{titles_list}

Return ONLY a JSON object mapping each movie title to its reason string. Example:
{{"Movie A": "Same director with a brooding neo-noir atmosphere.", "Movie B": "Shares the tense survival thriller DNA."}}

No extra text, just the JSON object."""

        response = model.generate_content(prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        print(f"Gemini Similar Explanation Error: {e}")
        return {}
