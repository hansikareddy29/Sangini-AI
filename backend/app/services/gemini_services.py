import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
api_key = os.getenv("OPEN_ROUTER_API_KEY")

if not api_key:
    raise ValueError("OPEN_ROUTER_API_KEY not found.Please check your .env file!!")

client = OpenAI(
    api_key=api_key,
    base_url="https://openrouter.ai/api/v1"
)

def ask_gemini(prompt: str):
    response=client.chat.completions.create(
        model="google/gemini-2.5-flash",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        max_tokens=200
    )
    return response.choices[0].message.content