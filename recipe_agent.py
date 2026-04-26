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
YOUTUBE_URL = "https://google.serper.dev/videos"


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def search_web(query: str, num_results: int = 5) -> list[dict]:
    """Search web via Serper."""
    print(f"  🔍 Searching: '{query}'")
    response = requests.post(
        SERPER_URL,
        headers=SERPER_HEADERS,
        json={"q": query, "num": num_results}
    )
    if response.status_code == 200:
        return [
            {
                "title": r.get("title", ""),
                "snippet": r.get("snippet", ""),
                "link": r.get("link", "")
            }
            for r in response.json().get("organic", [])
        ]
    return []


def search_youtube(query: str) -> dict | None:
    """Search YouTube via Serper videos endpoint."""
    print(f"  📺 Searching YouTube: '{query}'")
    response = requests.post(
        YOUTUBE_URL,
        headers=SERPER_HEADERS,
        json={"q": query, "num": 3}
    )
    if response.status_code == 200:
        videos = response.json().get("videos", [])
        if videos:
            top = videos[0]
            return {
                "title": top.get("title", ""),
                "link": top.get("link", ""),
                "channel": top.get("channel", ""),
                "duration": top.get("duration", "")
            }
    return None


def call_gemini(messages: list, system_prompt: str) -> str:
    """Call Gemini via Locus."""
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
    raise Exception(f"Gemini error {response.status_code}: {response.text}")


# ─────────────────────────────────────────────
# Recipe Agent Node
# ─────────────────────────────────────────────

def recipe_agent_node(state: AgentState) -> AgentState:
    """
    Finds the best recipe for the recommended dish
    and a YouTube video to go with it.
    """
    print("\n🍳  [Recipe Agent] Finding recipe + YouTube video...\n")

    recommendations = state.get("recommendations", "")
    medical = state.get("medical_profile")
    conditions = medical.get("conditions", []) if medical else []
    conditions_str = ", ".join(conditions) if conditions else "none"

    # ── Step 1: Extract dish name from recommendation ──
    dish_prompt = """From the dietary recommendation below, extract ONLY the name of 
the main dish suggested. Return just the dish name, nothing else. 
Example: 'Grilled Salmon with Vegetables'"""

    dish_name = call_gemini(
        messages=[{"role": "user", "content": f"Recommendation:\n{recommendations}"}],
        system_prompt=dish_prompt
    ).strip()

    print(f"  🍽️  Dish identified: {dish_name}")

    # ── Step 2: Search for recipe ──
    print("\n📡 Step 1: Searching for best recipe...")
    recipe_results = search_web(
        f"healthy {dish_name} recipe for {conditions_str} step by step",
        num_results=5
    )

    # ── Step 3: Search YouTube ──
    print("\n📡 Step 2: Finding YouTube video...")
    youtube_video = search_youtube(f"healthy {dish_name} recipe for {conditions_str}")

    # ── Step 4: Generate clean recipe with Gemini ──
    print("\n🤖 Step 3: Generating step-by-step recipe via Gemini...\n")

    recipe_context = "\n".join([
        f"- {r['title']}: {r['snippet']}"
        for r in recipe_results
    ])

    system_prompt = f"""You are a professional chef and dietary expert.
The user has these health conditions: {conditions_str}.

Using the web search results provided, create a clear, detailed recipe for: {dish_name}

Format your response EXACTLY like this:

## 🍽️ {dish_name}

### 📝 Ingredients
- List each ingredient with quantity

### 👨‍🍳 Instructions
1. Step one
2. Step two
(etc.)

### ⏱️ Time
- Prep: X mins
- Cook: X mins
- Total: X mins

### 💪 Health Benefits
- Brief note on why this is good for the user's conditions

Keep it practical, clear and healthy."""

    recipe = call_gemini(
        messages=[{"role": "user", "content": f"Recipe search results:\n{recipe_context}"}],
        system_prompt=system_prompt
    )

    # ── Step 5: Display results ──
    print("=" * 55)
    print("🍳  RECIPE AGENT OUTPUT")
    print("=" * 55)
    print(recipe)

    if youtube_video:
        print(f"\n📺 YouTube Video: {youtube_video['title']}")
        print(f"   Link: {youtube_video['link']}")
        print(f"   Channel: {youtube_video['channel']}")
    print("=" * 55 + "\n")

    return {
        **state,
        "recipe": recipe,
        "youtube_video": youtube_video,
        "dish_name": dish_name,
        "next_action": "order_agent"
    }