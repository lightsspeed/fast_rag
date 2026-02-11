
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from groq import Groq
from app.core.config import settings

client = Groq(api_key=settings.GROQ_API_KEY)

try:
    models = client.models.list()
    print("Available Models:")
    for m in models.data:
        print(f"- {m.id}")
except Exception as e:
    print(f"Error listing models: {e}")
