import requests
import os
from dotenv import load_dotenv

load_dotenv()

LOCUS_API_KEY = os.getenv("LOCUS_API_KEY")
BASE_URL = "https://beta-api.paywithlocus.com/api/wrapped/gemini/chat"

HEADERS = {
    "Authorization": f"Bearer {LOCUS_API_KEY}",
    "Content-Type": "application/json"
}

SYSTEM_PROMPT = """You are a friendly and knowledgeable dietary assistant. 
You help users with:
- Nutritional information about foods
- Healthy meal recommendations
- Recipe suggestions
- Dietary advice based on health goals
Keep your answers concise, practical, and easy to understand."""


def chat_with_gemini(messages: list) -> str:
    """Send messages to Gemini via Locus and return the response."""
    payload = {
        "model": "gemini-2.5-flash",
        "messages": messages,
        "systemInstruction": SYSTEM_PROMPT,
        "temperature": 0.7,
        "maxOutputTokens": 1024
    }

    response = requests.post(BASE_URL, headers=HEADERS, json=payload)

    if response.status_code == 200:
        data = response.json()
        # Extract text from Gemini response
        return data["data"]["candidates"][0]["content"]["parts"][0]["text"]
    else:
        return f"Error {response.status_code}: {response.json().get('message', 'Unknown error')}"


def check_balance() -> str:
    """Check remaining Locus wallet balance."""
    resp = requests.get(
        "https://beta-api.paywithlocus.com/api/pay/balance",
        headers=HEADERS
    )
    if resp.status_code == 200:
        data = resp.json()["data"]
        usdc = data.get("usdc_balance", "0.0")
        promo = data.get("promo_credit_balance", "0")
        return f"💰 Balance — USDC: ${usdc} | Promo Credits: ${promo}"
    return "Could not fetch balance."


def main():
    print("=" * 50)
    print("🥗  Dietary Assistant (Powered by Locus + Gemini)")
    print("=" * 50)
    print(check_balance())
    print("\nType 'quit' to exit | 'balance' to check credits\n")

    conversation_history = []

    while True:
        user_input = input("You: ").strip()

        if not user_input:
            continue
        if user_input.lower() == "quit":
            print("Goodbye! Stay healthy 🥦")
            break
        if user_input.lower() == "balance":
            print(check_balance())
            continue

        # Add user message to history
        conversation_history.append({
            "role": "user",
            "content": user_input
        })

        print("Gemini: ", end="", flush=True)
        response = chat_with_gemini(conversation_history)
        print(response)
        print()

        # Add assistant response to history for multi-turn conversation
        conversation_history.append({
            "role": "model",
            "content": response
        })


if __name__ == "__main__":
    main()