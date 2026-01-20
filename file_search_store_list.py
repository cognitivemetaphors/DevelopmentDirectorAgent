import os
from google import genai
from dotenv import load_dotenv

# Load the environment variables from the .env file
load_dotenv()

# Access the API key from the environment
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY not found. Check your .env file.")

client = genai.Client(api_key=api_key)

print("--- Your File Search Stores ---")
# Iterate through all stores in your project
for store in client.file_search_stores.list():
    print(f"Display Name: {store.display_name}")
    print(f"ID:           {store.name}")
    print("-" * 30)
