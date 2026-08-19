from google import genai
from app.config import settings

# Initialize official Google GenAI Client
client = genai.Client(api_key=settings.GEMINI_API_KEY)