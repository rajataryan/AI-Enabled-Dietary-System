import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from state import AgentState, MedicalProfile, PantryItem

load_dotenv()

LOCUS_API_KEY = os.getenv("LOCUS_API_KEY")
HEADERS = {
    "Authorization": f"Bearer {LOCUS_API_KEY}",
    "Content-Type": "application/json"
}
GEMINI_URL = "https://beta-api.paywithlocus.com/api/wrapped/gemini/chat"


# ─────────────────────────────────────────────
# Gemini helper (used only for medical notes)
# ─────────────────────────────────────────────

def call_gemini(messages: list, system_prompt: str) -> str:
    """Call Gemini via Locus wrapped API."""
    payload = {
        "model": "gemini-2.5-flash",
        "messages": messages,
        "systemInstruction": system_prompt,
        "temperature": 0.7,
        "maxOutputTokens": 1024
    }
    response = requests.post(GEMINI_URL, headers=HEADERS, json=payload)
    if response.status_code == 200:
        return response.json()["data"]["candidates"][0]["content"]["parts"][0]["text"]
    else:
        raise Exception(f"Gemini API error {response.status_code}: {response.text}")


# ─────────────────────────────────────────────
# Mode 1: Food Request Node
# ─────────────────────────────────────────────

def food_request_node(state: AgentState) -> AgentState:
    """
    Collects what the user wants to eat right now.
    Does NOT make recommendations — just captures the request
    and passes everything to the Nutrition Agent.
    """
    print("\n🍽️  [Intake Agent] Got your food request!\n")

    food_request = state.get("food_request", "")
    medical = state.get("medical_profile")
    pantry = state.get("pantry", [])

    available_items = [item["name"] for item in pantry if item["available"]]
    conditions = medical.get("conditions", []) if medical else []
    allergies = medical.get("allergies", []) if medical else []

    # Just summarise what was collected — no recommendations here
    print(f"  📝 Request      : {food_request}")
    print(f"  🏥 Conditions   : {', '.join(conditions) if conditions else 'None'}")
    print(f"  ⚠️  Allergies    : {', '.join(allergies) if allergies else 'None'}")
    print(f"  📦 Pantry items : {', '.join(available_items) if available_items else 'Empty'}")
    print("\n✅ Data collected — passing to Nutrition Agent...\n")

    return {
        **state,
        "next_action": "nutrition_agent"
    }


# ─────────────────────────────────────────────
# Mode 2: Medical Update Node
# ─────────────────────────────────────────────

def medical_update_node(state: AgentState) -> AgentState:
    """
    Handles updating the user's medical profile.
    User can add conditions, allergies, or paste doctor notes.
    """
    print("\n🏥  [Medical Update Agent] Updating your medical profile...\n")

    current_profile: MedicalProfile = state.get("medical_profile") or {
        "conditions": [],
        "allergies": [],
        "doctor_notes": [],
        "last_updated": None
    }

    print("Current Medical Profile:")
    print(f"  Conditions  : {current_profile['conditions'] or 'None'}")
    print(f"  Allergies   : {current_profile['allergies'] or 'None'}")
    print(f"  Last Updated: {current_profile['last_updated'] or 'Never'}\n")

    print("What would you like to update?")
    print("  1. Add a health condition")
    print("  2. Add an allergy")
    print("  3. Paste doctor report / notes")
    print("  4. Done\n")

    while True:
        choice = input("Choose (1-4): ").strip()

        if choice == "1":
            condition = input("Enter condition (e.g. diabetes): ").strip()
            if condition:
                current_profile["conditions"].append(condition)
                print(f"✅ Added condition: {condition}")

        elif choice == "2":
            allergy = input("Enter allergy (e.g. peanuts): ").strip()
            if allergy:
                current_profile["allergies"].append(allergy)
                print(f"✅ Added allergy: {allergy}")

        elif choice == "3":
            print("Paste your doctor's notes (press Enter twice when done):")
            lines = []
            while True:
                line = input()
                if line == "":
                    break
                lines.append(line)
            notes = " ".join(lines)

            if notes:
                system_prompt = """You are a medical data extractor. 
Extract any health conditions, allergies, medications, or dietary restrictions 
from the doctor's notes. Return a brief structured summary."""
                messages = [{"role": "user", "content": f"Doctor notes: {notes}"}]
                summary = call_gemini(messages, system_prompt)
                current_profile["doctor_notes"].append(f"[{datetime.now().strftime('%Y-%m-%d')}] {notes}")
                print(f"\n🤖 Extracted from report:\n{summary}\n")

        elif choice == "4":
            break

        else:
            print("Invalid choice, try again.")

    current_profile["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    print("\n✅ Medical profile updated successfully!\n")

    return {
        **state,
        "medical_profile": current_profile,
        "next_action": "end"
    }


# ─────────────────────────────────────────────
# Mode 3: Pantry Tracker Node
# ─────────────────────────────────────────────

def pantry_update_node(state: AgentState) -> AgentState:
    """
    Handles the pantry/ingredient tracker.
    User can add items, mark them as available/unavailable.
    """
    print("\n📦  [Pantry Tracker Agent] Managing your pantry...\n")

    pantry: list[PantryItem] = state.get("pantry") or []

    def display_pantry():
        if not pantry:
            print("  (Pantry is empty)\n")
            return
        print("  Your Pantry:")
        for i, item in enumerate(pantry):
            status = "✅" if item["available"] else "❌"
            print(f"  {i + 1}. {status} {item['name']}")
        print()

    print("What would you like to do?")
    print("  1. Add a new item")
    print("  2. Mark item as used up (unavailable)")
    print("  3. Mark item as restocked (available)")
    print("  4. View pantry")
    print("  5. Done\n")

    while True:
        display_pantry()
        choice = input("Choose (1-5): ").strip()

        if choice == "1":
            item_name = input("Enter item name (e.g. tomatoes): ").strip()
            if item_name:
                existing = next((i for i, x in enumerate(pantry) if x["name"].lower() == item_name.lower()), None)
                if existing is not None:
                    pantry[existing]["available"] = True
                    print(f"✅ '{item_name}' already in pantry — marked as available.")
                else:
                    pantry.append({"name": item_name, "available": True})
                    print(f"✅ Added '{item_name}' to pantry.")

        elif choice == "2":
            item_name = input("Which item is used up? ").strip()
            found = next((i for i, x in enumerate(pantry) if x["name"].lower() == item_name.lower()), None)
            if found is not None:
                pantry[found]["available"] = False
                print(f"❌ '{item_name}' marked as used up.")
            else:
                print(f"Item '{item_name}' not found in pantry.")

        elif choice == "3":
            item_name = input("Which item was restocked? ").strip()
            found = next((i for i, x in enumerate(pantry) if x["name"].lower() == item_name.lower()), None)
            if found is not None:
                pantry[found]["available"] = True
                print(f"✅ '{item_name}' marked as available.")
            else:
                print(f"Item '{item_name}' not found. Adding it now.")
                pantry.append({"name": item_name, "available": True})

        elif choice == "4":
            display_pantry()

        elif choice == "5":
            break

        else:
            print("Invalid choice, try again.")

    print("\n✅ Pantry updated!\n")

    return {
        **state,
        "pantry": pantry,
        "next_action": "end"
    }


# ─────────────────────────────────────────────
# Router: Decides which mode to enter
# ─────────────────────────────────────────────

def intake_router(state: AgentState) -> str:
    """Routes to the correct intake node based on current_mode."""
    mode = state.get("current_mode", "")
    if mode == "food_request":
        return "food_request_node"
    elif mode == "medical_update":
        return "medical_update_node"
    elif mode == "pantry_update":
        return "pantry_update_node"
    else:
        return "end"