import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "placeholder")

if GEMINI_API_KEY == "placeholder":
    print("Warning: GEMINI_API_KEY is not set in environment.")