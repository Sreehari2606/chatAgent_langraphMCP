import json
from langchain_google_genai import ChatGoogleGenerativeAI

llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key="AIzaSyDJUeiaChgjI39eQbQEMhmV3ETG8A4iwOg", temperature=0.2)

def llm_invoke(prompt: str) -> dict:
    try:
        response = llm.invoke(prompt)
        return {"generate": response.content.strip()}
    except Exception as e:
        return {"generate": f"Error: {e}"}

def llm_invoke_json(prompt: str) -> dict:
    try:
        json_prompt = f"{prompt}\n\nIMPORTANT: Respond ONLY with valid JSON, no markdown, no code blocks."
        response = llm.invoke(json_prompt)
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        return json.loads(content)
    except json.JSONDecodeError:
        return {"response": response.content.strip() if 'response' in dir() else "Error parsing response", "confidence": 0.5}
    except Exception as e:
        return {"response": f"Error: {e}", "confidence": 0.0}
