import requests

SYSTEM_PROMPT = """
You are a hospital receptionist.

Rules:
- ALWAYS reply in English
- Keep answers under 15 words
- Be direct and helpful
- Ask follow-up if needed
"""

def generate_reply(user_text, history):

    history_text = ""
    for msg in history:
        history_text += f"{msg['role']}: {msg['content']}\n"

    prompt = f"""
{SYSTEM_PROMPT}

Conversation:
{history_text}

User: {user_text}
Assistant:
"""

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "llama3",
            "prompt": prompt,
            "stream": False
        }
    )

    return response.json()["response"]