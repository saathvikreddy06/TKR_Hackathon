import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "placeholder")

if GEMINI_API_KEY == "placeholder":
    print("Warning: GEMINI_API_KEY is not set in environment.")