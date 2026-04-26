import os
import requests
from dotenv import load_dotenv
from state import AgentState

load_dotenv()

LOCUS_API_KEY = os.getenv("LOCUS_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

LOCUS_HEADERS = {
    "Authorization": f"Bearer {LOCUS_API_KEY}",
    "Content-Type": "application/json"
}
SERPER_HEADERS = {
    "X-API-KEY": SERPER_API_KEY,
    "Content-Type": "application/json"
}

GEMINI_URL = "https://beta-api.paywithlocus.com/api/wrapped/gemini/chat"
SERPER_URL = "https://google.serper.dev/search"


# ─────────────────────────────────────────────
# Serper Search Helper
# ─────────────────────────────────────────────

def search_web(query: str, num_results: int = 5) -> list[dict]:
    """Search the web using Serper (Google Search API)."""
    print(f"  🔍 Searching: '{query}'")
    payload = {
        "q": query,
        "num": num_results
    }
    response = requests.post(SERPER_URL, headers=SERPER_HEADERS, json=payload)
    if response.status_code == 200:
        results = response.json().get("organic", [])
        return [
            {
                "title": r.get("title", ""),
                "snippet": r.get("snippet", ""),
                "link": r.get("link", "")
            }
            for r in results
        ]
    else:
        print(f"  ⚠️  Serper error {response.status_code}: {response.text}")
        return []


# ─────────────────────────────────────────────
# Gemini Helper (via Locus)
# ─────────────────────────────────────────────

def call_gemini(messages: list, system_prompt: str) -> str:
    """Call Gemini via Locus wrapped API."""
    payload = {
        "model": "gemini-2.5-flash",
        "messages": messages,
        "systemInstruction": system_prompt,
        "temperature": 0.7,
        "maxOutputTokens": 2048
    }
    response = requests.post(GEMINI_URL, headers=LOCUS_HEADERS, json=payload)
    if response.status_code == 200:
        return response.json()["data"]["candidates"][0]["content"]["parts"][0]["text"]
    else:
        raise Exception(f"Gemini API error {response.status_code}: {response.text}")


# ─────────────────────────────────────────────
# Nutrition Agent Node
# ─────────────────────────────────────────────

def nutrition_agent_node(state: AgentState) -> AgentState:
    """
    Searches the web for best dishes + nutritional values
    based on the user's food request and medical profile.
    Then uses Gemini to analyse and give a safe recommendation.
    """
    print("\n🥦  [Nutrition Agent] Searching for the best options for you...\n")

    # Pull data from state
    food_request = state.get("food_request", "")
    medical = state.get("medical_profile")
    pantry = state.get("pantry", [])

    conditions = medical.get("conditions", []) if medical else []
    allergies = medical.get("allergies", []) if medical else []
    available_items = [item["name"] for item in pantry if item["available"]]

    conditions_str = ", ".join(conditions) if conditions else "none"
    allergies_str = ", ".join(allergies) if allergies else "none"
    pantry_str = ", ".join(available_items) if available_items else "empty pantry"

    # ── Step 1: Search for best dishes for the condition ──
    print("📡 Step 1: Finding best dishes for your condition...")
    dish_query = f"best healthy dishes for {conditions_str} {food_request}".strip()
    dish_results = search_web(dish_query, num_results=5)

    # ── Step 2: Search for nutritional values ──
    print("\n📡 Step 2: Getting nutritional values...")
    nutrition_query = f"nutritional values {food_request} {conditions_str} diet"
    nutrition_results = search_web(nutrition_query, num_results=5)

    # ── Step 3: Format search results for Gemini ──
    def format_results(results: list[dict]) -> str:
        if not results:
            return "No results found."
        return "\n".join([
            f"- {r['title']}: {r['snippet']}"
            for r in results
        ])

    dish_context = format_results(dish_results)
    nutrition_context = format_results(nutrition_results)

    # ── Step 4: Ask Gemini to analyse + check conflicts ──
    print("\n🤖 Step 3: Analysing results and checking for conflicts...\n")

    system_prompt = f"""You are an expert dietary and nutrition analyst.

The user has the following profile:
- Health conditions: {conditions_str}
- Allergies: {allergies_str}
- Available pantry items: {pantry_str}
- Food request: {food_request}

You have been given web search results about recommended dishes and nutritional values.
Your job is to:
1. Identify the TOP 2-3 best dish recommendations that suit their condition
2. Provide key nutritional values for each dish
3. Check for any conflicts with their medical conditions or allergies
4. If there is a conflict, suggest a safe alternative instead
5. List what ingredients are missing from their pantry
6. Give one clear FINAL recommendation

Be specific, practical and concise. Format your response clearly with sections."""

    user_message = f"""
Dish search results:
{dish_context}

Nutritional value search results:
{nutrition_context}

Please analyse these results and give me your recommendation.
"""

    analysis = call_gemini(
        messages=[{"role": "user", "content": user_message}],
        system_prompt=system_prompt
    )

    # ── Step 5: Extract missing ingredients via Gemini ──
    missing_prompt = """Based on the recommendation above, list ONLY the ingredient names 
that are missing from the pantry. Return them as a simple comma-separated list with no 
extra text. Example: tomatoes, olive oil, salmon"""

    missing_response = call_gemini(
        messages=[
            {"role": "user", "content": user_message},
            {"role": "model", "content": analysis},
            {"role": "user", "content": missing_prompt}
        ],
        system_prompt=system_prompt
    )

    missing_ingredients = [
        item.strip()
        for item in missing_response.split(",")
        if item.strip()
    ]

    # ── Step 6: Display results ──
    print("=" * 55)
    print("🥗  NUTRITION AGENT RECOMMENDATION")
    print("=" * 55)
    print(analysis)
    print("\n" + "-" * 55)
    print(f"🛒 Missing ingredients to order: {', '.join(missing_ingredients) if missing_ingredients else 'None — pantry has everything!'}")
    print("-" * 55 + "\n")

    return {
        **state,
        "recommendations": analysis,
        "nutrition_info": nutrition_context,
        "missing_ingredients": missing_ingredients,
        "next_action": "recipe_agent"
    }