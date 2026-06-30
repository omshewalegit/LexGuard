from dotenv import load_dotenv
import os

load_dotenv(override=True)
key = os.getenv("GROQ_API_KEY", "")
print(f"Loaded key ends with: ...{key[-6:]}")

from langchain_groq import ChatGroq

llm = ChatGroq(api_key=key, model_name="llama-3.3-70b-versatile", max_tokens=20)
try:
    response = llm.invoke("Say hello in exactly 3 words.")
    print("SUCCESS — key is working:")
    print(response.content)
except Exception as e:
    print("FAILED:")
    print(e)