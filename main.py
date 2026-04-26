from graph import build_graph
from state import AgentState


def get_user_mode() -> str:
    """Ask the user which mode they want to use."""
    print("\n" + "=" * 50)
    print("🥗  Dietary Assistant — Powered by Locus + Gemini")
    print("=" * 50)
    print("\nWhat would you like to do?\n")
    print("  1. 🍽️  I want to eat something (Food Request)")
    print("  2. 🏥  Update my medical profile / doctor report")
    print("  3. 📦  Manage my pantry / ingredient tracker")
    print("  4. 🚪  Exit\n")

    choice = input("Choose (1-4): ").strip()

    mode_map = {
        "1": "food_request",
        "2": "medical_update",
        "3": "pantry_update",
    }
    return mode_map.get(choice, "exit")


def main():
    # Build the graph once
    app = build_graph()

    # Persistent state across sessions (in memory for now, Supabase later)
    persistent_state: AgentState = {
        "messages": [],
        "food_request": None,
        "medical_profile": None,
        "pantry": [],
        "recommendations": None,
        "missing_ingredients": None,
        "recipe": None,
        "nutrition_info": None,
        "current_mode": None,
        "next_action": None,
    }

    while True:
        mode = get_user_mode()

        if mode == "exit":
            print("\n👋 Goodbye! Stay healthy!\n")
            break

        # Mode-specific input
        if mode == "food_request":
            food_input = input("\nWhat are you craving or what do you want to eat? ").strip()
            persistent_state["food_request"] = food_input

        # Update mode and run graph
        persistent_state["current_mode"] = mode

        # Run the graph
        result = app.invoke(persistent_state)

        # Update persistent state with results
        persistent_state.update(result)

        print("\n" + "-" * 50)
        input("Press Enter to continue...\n")


if __name__ == "__main__":
    main()