import os
from dotenv import load_dotenv

load_dotenv()

import os
import random
from typing import List
from dotenv import load_dotenv

load_dotenv()

class Config:
    _GEMINI_KEYS = os.getenv("GEMINI_API_KEYS", "").split(",")
    PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY")
    
    # Paths
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ASSETS_DIR = os.path.join(BASE_DIR, "assets")
    OUTPUT_DIR = os.path.join(BASE_DIR, "output")
    
    # Models - Updated to latest/requested
    # Scriptwriter: Using reliable model to avoid rate limits
    SCRIPT_MODEL = "models/gemini-flash-latest" 
    
    # Director: The Brain (as requested)
    DIRECTOR_MODEL = "models/gemini-pro-latest"
    
    # Clipper: Fast video analysis
    CLIPPER_MODEL = "models/gemini-flash-latest"
    
    # Keyword Extraction (Visual Agent)
    KEYWORD_MODEL = "models/gemini-flash-latest"

    # TTS & Imagen (Specific models)
    TTS_MODEL = "models/gemini-2.5-pro-preview-tts" 
    TTS_VOICE = "Algeiba"
    IMAGEN_MODEL = "imagen-3.0-generate-001"

    @staticmethod
    def validate():
        if not Config._GEMINI_KEYS or not Config._GEMINI_KEYS[0]:
            raise ValueError("GEMINI_API_KEYS are missing in .env")
        if not Config.PIXABAY_API_KEY:
            raise ValueError("PIXABAY_API_KEY is missing in .env")

    @staticmethod
    def get_gemini_key() -> str:
        """Returns a random Gemini API key from the pool."""
        return random.choice(Config._GEMINI_KEYS).strip()

