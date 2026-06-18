import g4f
from g4f.client import Client

try:
    print(g4f.models.gemini_pro_vision)
except Exception as e:
    print("ERROR:", e)
