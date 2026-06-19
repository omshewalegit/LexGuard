import os
from dotenv import load_dotenv
load_dotenv()
key = os.getenv("GROQ_API_KEY")
print("Key loaded:", repr(key))
print("Length:", len(key) if key else 0)