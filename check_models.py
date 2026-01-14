import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    with open("models_list.txt", "w") as f:
        f.write("Error: GEMINI_API_KEY not found in .env")
else:
    genai.configure(api_key=GEMINI_API_KEY)
    try:
        with open("models_list.txt", "w") as f:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    f.write(f"{m.name}\n")
    except Exception as e:
        with open("models_list.txt", "w") as f:
            f.write(f"Error listing models: {e}")
