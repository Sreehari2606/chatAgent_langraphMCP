"""
LLM Module - Simple wrapper for Google Gemini
"""
import json
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

# Load environment variables from .env file
load_dotenv()

# Initialize LLM
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.2
)


def llm_invoke(prompt: str) -> dict:
    """Simple text completion"""
    try:
        response = llm.invoke(prompt)
        return {"generate": response.content.strip()}
    except Exception as e:
        return {"generate": f"Error: {e}"}


def llm_invoke_json(prompt: str) -> dict:
    """Get JSON response from LLM"""
    try:
        json_prompt = f"{prompt}\n\nRespond ONLY with valid JSON, no markdown."
        response = llm.invoke(json_prompt)
        content = response.content.strip()
        
        # Clean markdown code blocks if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        
        return json.loads(content)
    except json.JSONDecodeError:
        return {"response": "Could not parse JSON response"}
    except Exception as e:
        return {"response": f"Error: {e}"}
