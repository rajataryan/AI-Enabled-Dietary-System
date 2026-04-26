import gradio as gr
import requests
import os
import threading
from datetime import datetime
from dotenv import load_dotenv
from state import AgentState
from nutrition_agent import nutrition_agent_node

load_dotenv()

# ─────────────────────────────────────────────
# In-memory state
# ─────────────────────────────────────────────

app_state: AgentState = {
    "messages": [],
    "food_request": None,
    "medical_profile": {
        "conditions": [],
        "allergies": [],
        "doctor_notes": [],
        "last_updated": None
    },
    "pantry": [],
    "recommendations": None,
    "missing_ingredients": None,
    "recipe": None,
    "nutrition_info": None,
    "current_mode": None,
    "next_action": None,
}

state_lock = threading.Lock()

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def get_pantry_display():
    pantry = app_state.get("pantry", [])
    if not pantry:
        return "No items in pantry yet."
    return "\n".join([
        f"{'✅' if item['available'] else '❌'} {item['name']}"
        for item in pantry
    ])


def get_medical_display():
    profile = app_state.get("medical_profile", {})
    conditions = profile.get("conditions", [])
    allergies = profile.get("allergies", [])
    notes = profile.get("doctor_notes", [])
    updated = profile.get("last_updated", "Never")
    return (
        f"🏥 Conditions   : {', '.join(conditions) if conditions else 'None'}\n"
        f"⚠️  Allergies    : {', '.join(allergies) if allergies else 'None'}\n"
        f"📋 Doctor Notes : {len(notes)} note(s) saved\n"
        f"🕐 Last Updated : {updated}"
    )


# ─────────────────────────────────────────────
# PAGE 1: Food Request (runs in thread)
# ─────────────────────────────────────────────

def run_nutrition_agent(state_copy):
    """Runs in a background thread — no blocking of Gradio."""
    try:
        result = nutrition_agent_node(state_copy)
        return result, None
    except Exception as e:
        return None, str(e)


def handle_food_request(food_input):
    if not food_input.strip():
        yield "⚠️ Please enter what you'd like to eat.", "", "", "", ""
        return

    with state_lock:
        app_state["food_request"] = food_input

    medical = app_state.get("medical_profile", {})
    pantry = app_state.get("pantry", [])
    conditions = medical.get("conditions", [])
    allergies = medical.get("allergies", [])
    available = [i["name"] for i in pantry if i["available"]]

    intake_summary = (
        f"📝 Request      : {food_input}\n"
        f"🏥 Conditions   : {', '.join(conditions) if conditions else 'None'}\n"
        f"⚠️  Allergies    : {', '.join(allergies) if allergies else 'None'}\n"
        f"📦 Pantry items : {', '.join(available) if available else 'Empty'}\n\n"
        f"⏳ Searching web + analysing..."
    )

    # Show loading state immediately
    yield intake_summary, "⏳ Please wait — searching Serper + Gemini...", "", "", ""

    # Run agent in background thread
    result_container = {}

    def worker():
        state_copy = dict(app_state)
        result, error = run_nutrition_agent(state_copy)
        result_container["result"] = result
        result_container["error"] = error

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()  # Wait for thread to finish

    error = result_container.get("error")
    result = result_container.get("result")

    if error:
        yield intake_summary, f"❌ Error: {error}", "", "", ""
        return

    with state_lock:
        app_state.update(result)

    recommendations = result.get("recommendations", "No recommendation generated.")
    nutrition_info = result.get("nutrition_info", "")
    missing = result.get("missing_ingredients", [])
    missing_str = "\n".join([f"🛒 {item}" for item in missing]) if missing else "✅ You have everything!"

    sources = "🔗 Sources searched via Serper (Google):\n\n"
    if nutrition_info:
        for line in nutrition_info.split("\n")[:8]:
            if line.strip():
                sources += f"• {line.strip()}\n"

    intake_done = intake_summary.replace("⏳ Searching web + analysing...", "✅ Done!")
    yield intake_done, recommendations, nutrition_info, missing_str, sources


# ─────────────────────────────────────────────
# PAGE 2: Medical Profile
# ─────────────────────────────────────────────

def add_condition(condition):
    if not condition.strip():
        return get_medical_display(), "⚠️ Please enter a condition.", ""
    with state_lock:
        app_state["medical_profile"]["conditions"].append(condition.strip())
        app_state["medical_profile"]["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    return get_medical_display(), f"✅ Added: {condition.strip()}", ""


def add_allergy(allergy):
    if not allergy.strip():
        return get_medical_display(), "", "⚠️ Please enter an allergy."
    with state_lock:
        app_state["medical_profile"]["allergies"].append(allergy.strip())
        app_state["medical_profile"]["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    return get_medical_display(), "", f"✅ Added: {allergy.strip()}"


def add_doctor_notes(notes):
    if not notes.strip():
        return get_medical_display(), "⚠️ Please paste some notes."
    LOCUS_API_KEY = os.getenv("LOCUS_API_KEY")
    headers = {
        "Authorization": f"Bearer {LOCUS_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gemini-2.5-flash",
        "messages": [{"role": "user", "content": f"Doctor notes: {notes}"}],
        "systemInstruction": "You are a medical data extractor. Extract health conditions, allergies, medications, or dietary restrictions. Return a brief structured summary.",
        "temperature": 0.5,
        "maxOutputTokens": 512
    }
    try:
        resp = requests.post(
            "https://beta-api.paywithlocus.com/api/wrapped/gemini/chat",
            headers=headers, json=payload, timeout=30
        )
        summary = resp.json()["data"]["candidates"][0]["content"]["parts"][0]["text"]
        with state_lock:
            app_state["medical_profile"]["doctor_notes"].append(
                f"[{datetime.now().strftime('%Y-%m-%d')}] {notes}"
            )
            app_state["medical_profile"]["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        return get_medical_display(), f"✅ Notes saved!\n\n🤖 Extracted:\n{summary}"
    except Exception as e:
        return get_medical_display(), f"❌ Error: {str(e)}"


def clear_conditions():
    with state_lock:
        app_state["medical_profile"]["conditions"] = []
        app_state["medical_profile"]["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    return get_medical_display(), "🗑️ Conditions cleared.", ""


def clear_allergies():
    with state_lock:
        app_state["medical_profile"]["allergies"] = []
        app_state["medical_profile"]["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    return get_medical_display(), "", "🗑️ Allergies cleared."


# ─────────────────────────────────────────────
# PAGE 3: Pantry Tracker
# ─────────────────────────────────────────────

def add_pantry_item(item_name):
    if not item_name.strip():
        return get_pantry_display(), "⚠️ Please enter an item name."
    name = item_name.strip()
    with state_lock:
        pantry = app_state["pantry"]
        existing = next((i for i, x in enumerate(pantry) if x["name"].lower() == name.lower()), None)
        if existing is not None:
            pantry[existing]["available"] = True
            return get_pantry_display(), f"✅ '{name}' marked as available."
        pantry.append({"name": name, "available": True})
    return get_pantry_display(), f"✅ Added '{name}' to pantry."


def mark_used_up(item_name):
    if not item_name.strip():
        return get_pantry_display(), "⚠️ Please enter an item name."
    name = item_name.strip()
    with state_lock:
        pantry = app_state["pantry"]
        found = next((i for i, x in enumerate(pantry) if x["name"].lower() == name.lower()), None)
        if found is not None:
            pantry[found]["available"] = False
            return get_pantry_display(), f"❌ '{name}' marked as used up."
    return get_pantry_display(), f"⚠️ '{name}' not found."


def mark_restocked(item_name):
    if not item_name.strip():
        return get_pantry_display(), "⚠️ Please enter an item name."
    name = item_name.strip()
    with state_lock:
        pantry = app_state["pantry"]
        found = next((i for i, x in enumerate(pantry) if x["name"].lower() == name.lower()), None)
        if found is not None:
            pantry[found]["available"] = True
            return get_pantry_display(), f"✅ '{name}' restocked."
        pantry.append({"name": name, "available": True})
    return get_pantry_display(), f"✅ '{name}' added and available."


def clear_pantry():
    with state_lock:
        app_state["pantry"] = []
    return get_pantry_display(), "🗑️ Pantry cleared."


# ─────────────────────────────────────────────
# BUILD GRADIO UI
# ─────────────────────────────────────────────

theme = gr.themes.Soft(
    primary_hue="emerald",
    secondary_hue="teal",
    neutral_hue="slate",
    font=[gr.themes.GoogleFont("DM Sans"), "sans-serif"],
)

with gr.Blocks(
    theme=theme,
    title="🥗 Dietary Assistant",
    css="footer { display: none !important; }"
) as demo:

    gr.Markdown("# 🥗 Dietary Assistant\n*Powered by Locus + Gemini + Serper*")

    with gr.Tab("🍽️ Food Request"):
        gr.Markdown("### What do you want to eat? I'll find the best options for your health profile.")
        with gr.Row():
            with gr.Column(scale=1):
                food_input = gr.Textbox(
                    label="What are you craving?",
                    placeholder="e.g. Something light and healthy, maybe Indian food...",
                    lines=3
                )
                submit_btn = gr.Button("🔍 Find Best Options", variant="primary", size="lg")
                intake_box = gr.Textbox(label="📋 Intake Summary", lines=7, interactive=False)

            with gr.Column(scale=2):
                with gr.Tabs():
                    with gr.Tab("🥗 Recommendation"):
                        recommendation_box = gr.Textbox(label="AI Recommendation", lines=16, interactive=False)
                    with gr.Tab("🔬 Nutrition Info"):
                        nutrition_box = gr.Textbox(label="Nutritional Data", lines=16, interactive=False)
                    with gr.Tab("🛒 Missing Ingredients"):
                        missing_box = gr.Textbox(label="Items to Order", lines=16, interactive=False)
                    with gr.Tab("🔗 Sources"):
                        sources_box = gr.Textbox(label="Search Sources", lines=16, interactive=False)

        submit_btn.click(
            fn=handle_food_request,
            inputs=[food_input],
            outputs=[intake_box, recommendation_box, nutrition_box, missing_box, sources_box]
        )

    with gr.Tab("🏥 Medical Profile"):
        gr.Markdown("### Keep your medical profile updated for personalised recommendations.")
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("#### ➕ Health Conditions")
                condition_input = gr.Textbox(label="Condition", placeholder="e.g. Arthritis, Diabetes...")
                add_condition_btn = gr.Button("Add Condition", variant="primary")
                condition_status = gr.Textbox(label="Status", interactive=False, lines=1)

                gr.Markdown("#### ➕ Allergies")
                allergy_input = gr.Textbox(label="Allergy", placeholder="e.g. Peanuts, Gluten...")
                add_allergy_btn = gr.Button("Add Allergy", variant="primary")
                allergy_status = gr.Textbox(label="Status", interactive=False, lines=1)

                gr.Markdown("#### 📄 Doctor Notes")
                notes_input = gr.Textbox(label="Paste Report", placeholder="Paste doctor notes here...", lines=4)
                add_notes_btn = gr.Button("Save & Extract with AI", variant="primary")
                notes_status = gr.Textbox(label="Extracted Summary", interactive=False, lines=4)

            with gr.Column(scale=1):
                gr.Markdown("#### 📊 Current Profile")
                medical_display = gr.Textbox(
                    value=get_medical_display,
                    label="Your Medical Profile",
                    lines=8,
                    interactive=False
                )
                with gr.Row():
                    clear_conditions_btn = gr.Button("🗑️ Clear Conditions", variant="stop", size="sm")
                    clear_allergies_btn = gr.Button("🗑️ Clear Allergies", variant="stop", size="sm")

        add_condition_btn.click(add_condition, inputs=[condition_input], outputs=[medical_display, condition_status, allergy_status])
        add_allergy_btn.click(add_allergy, inputs=[allergy_input], outputs=[medical_display, condition_status, allergy_status])
        add_notes_btn.click(add_doctor_notes, inputs=[notes_input], outputs=[medical_display, notes_status])
        clear_conditions_btn.click(clear_conditions, outputs=[medical_display, condition_status, allergy_status])
        clear_allergies_btn.click(clear_allergies, outputs=[medical_display, condition_status, allergy_status])

    with gr.Tab("📦 Pantry Tracker"):
        gr.Markdown("### Track what's at home. The AI uses this to minimise what needs to be ordered.")
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("#### ➕ Add Item")
                pantry_input = gr.Textbox(label="Item Name", placeholder="e.g. Tomatoes, Olive Oil...")
                add_item_btn = gr.Button("Add to Pantry", variant="primary")

                gr.Markdown("#### 🔄 Update Item")
                update_input = gr.Textbox(label="Item Name", placeholder="e.g. Tomatoes...")
                with gr.Row():
                    used_btn = gr.Button("❌ Mark Used Up", variant="stop")
                    restock_btn = gr.Button("✅ Restocked", variant="secondary")

                clear_pantry_btn = gr.Button("🗑️ Clear All Pantry", variant="stop", size="sm")
                pantry_status = gr.Textbox(label="Status", interactive=False, lines=1)

            with gr.Column(scale=1):
                gr.Markdown("#### 📋 Current Pantry")
                pantry_display = gr.Textbox(
                    value=get_pantry_display,
                    label="Your Pantry",
                    lines=18,
                    interactive=False
                )

        add_item_btn.click(add_pantry_item, inputs=[pantry_input], outputs=[pantry_display, pantry_status])
        used_btn.click(mark_used_up, inputs=[update_input], outputs=[pantry_display, pantry_status])
        restock_btn.click(mark_restocked, inputs=[update_input], outputs=[pantry_display, pantry_status])
        clear_pantry_btn.click(clear_pantry, outputs=[pantry_display, pantry_status])


if __name__ == "__main__":
    demo.queue()
    demo.launch(share=False)