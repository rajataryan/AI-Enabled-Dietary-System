import os
import time
import requests
from dotenv import load_dotenv
from state import AgentState

load_dotenv()

LOCUS_API_KEY = os.getenv("LOCUS_API_KEY")
USER_LOCATION = os.getenv("USER_LOCATION", "Bengaluru, Karnataka, India")
DELIVERY_ADDRESS = os.getenv("DELIVERY_ADDRESS", "")
DELIVERY_PHONE = os.getenv("DELIVERY_PHONE", "")
STORE_EMAIL = os.getenv("STORE_EMAIL", "")
STORE_PASSWORD = os.getenv("STORE_PASSWORD", "")

LOCUS_HEADERS = {
    "Authorization": f"Bearer {LOCUS_API_KEY}",
    "Content-Type": "application/json"
}

BROWSER_USE_BASE = "https://beta-api.paywithlocus.com/api/wrapped/browser-use"
GEMINI_URL = "https://beta-api.paywithlocus.com/api/wrapped/gemini/chat"


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def call_gemini(messages: list, system_prompt: str) -> str:
    payload = {
        "model": "gemini-2.5-flash",
        "messages": messages,
        "systemInstruction": system_prompt,
        "temperature": 0.3,
        "maxOutputTokens": 512
    }
    response = requests.post(GEMINI_URL, headers=LOCUS_HEADERS, json=payload)
    if response.status_code == 200:
        return response.json()["data"]["candidates"][0]["content"]["parts"][0]["text"]
    raise Exception(f"Gemini error {response.status_code}: {response.text}")


def run_browser_task(task: str, max_steps: int = 100) -> str:
    """Start a browser automation task. Returns task ID."""
    print(f"  🌐 Starting browser task...")
    response = requests.post(
        f"{BROWSER_USE_BASE}/run-task",
        headers=LOCUS_HEADERS,
        json={"task": task, "maxSteps": max_steps}
    )
    print(f"  📥 Run task response: {response.status_code} — {response.text[:300]}")

    if response.status_code == 200:
        data = response.json()
        # Task ID can be nested in different ways
        task_id = (
            data.get("data", {}).get("id") or
            data.get("data", {}).get("taskId") or
            data.get("data", {}).get("task_id") or
            data.get("id") or
            data.get("taskId") or
            ""
        )
        return task_id
    raise Exception(f"Browser Use run-task error {response.status_code}: {response.text}")


def get_task_status(task_id: str) -> dict:
    """Check status of a browser task."""
    response = requests.post(
        f"{BROWSER_USE_BASE}/get-task-status",
        headers=LOCUS_HEADERS,
        json={"taskId": task_id}
    )
    if response.status_code == 200:
        return response.json().get("data", {})
    return {}


def get_task_result(task_id: str) -> dict:
    """Get full result of a completed browser task."""
    response = requests.post(
        f"{BROWSER_USE_BASE}/get-task",
        headers=LOCUS_HEADERS,
        json={"taskId": task_id}
    )
    if response.status_code == 200:
        return response.json().get("data", {})
    return {}


def wait_for_task(task_id: str, timeout: int = 300) -> dict:
    """Poll task status until complete or timeout."""
    print(f"  ⏳ Waiting for browser task (max {timeout}s)...")
    elapsed = 0
    poll_interval = 5
    # Terminal statuses from Browser Use docs
    terminal_statuses = {"finished", "completed", "done", "failed", "error", "stopped", "cancelled"}

    while elapsed < timeout:
        status_data = get_task_status(task_id)
        status = str(status_data.get("status", "")).lower()

        print(f"  📡 Status: '{status}' ({elapsed}s elapsed) | Raw: {str(status_data)[:100]}")

        if status in terminal_statuses:
            if status in {"finished", "completed", "done"}:
                return get_task_result(task_id)
            else:
                return {"error": f"Task ended with status: {status}", "status": status}

        time.sleep(poll_interval)
        elapsed += poll_interval

    # On timeout, still try to get whatever result exists
    return get_task_result(task_id) or {"error": "Task timed out", "status": "timeout"}


# ─────────────────────────────────────────────
# Order Agent Node
# ─────────────────────────────────────────────

def order_agent_node(state: AgentState) -> AgentState:
    """
    Uses Browser Use (via Locus) to automatically log into
    a grocery store, add missing ingredients to cart, and
    complete the checkout with saved delivery address and payment.
    """
    print("\n🛒  [Order Agent] Starting grocery ordering...\n")

    missing_ingredients = state.get("missing_ingredients", [])
    dish_name = state.get("dish_name", "the recommended dish")

    if not missing_ingredients:
        print("✅ No missing ingredients — nothing to order!")
        return {
            **state,
            "order_status": "nothing_to_order",
            "order_result": "All ingredients already available in pantry!",
            "next_action": "end"
        }

    print(f"  📍 Location       : {USER_LOCATION}")
    print(f"  🏠 Delivery addr  : {DELIVERY_ADDRESS or 'Not set in .env'}")
    print(f"  🛒 Items to order : {', '.join(missing_ingredients)}\n")

    # ── Step 1: Decide best store ──
    print("🤖 Step 1: Deciding best grocery store for your location...")
    store_prompt = f"""You are a grocery shopping assistant for someone in {USER_LOCATION}.

Which ONE grocery delivery website is most popular and delivers fastest in this area?
Choose from: Blinkit (blinkit.com), BigBasket (bigbasket.com), Swiggy Instamart (swiggy.com), 
Zepto (zeptonow.com), Amazon Fresh (amazon.in).

Return ONLY the full website URL. Example: https://www.blinkit.com
Nothing else — no explanation."""

    store_url = call_gemini(
        messages=[{"role": "user", "content": f"Location: {USER_LOCATION}"}],
        system_prompt=store_prompt
    ).strip().replace("```", "").strip()

    if not store_url.startswith("http"):
        store_url = "https://www.blinkit.com"

    print(f"  🏪 Selected store : {store_url}\n")

    # ── Step 2: Build browser task ──
    ingredients_list = "\n".join([f"- {item}" for item in missing_ingredients])

    login_instructions = ""
    if STORE_EMAIL and STORE_PASSWORD:
        login_instructions = f"""
2. Log in with these credentials:
   - Email/Phone: {STORE_EMAIL}
   - Password: {STORE_PASSWORD}"""

    address_instructions = ""
    if DELIVERY_ADDRESS:
        address_instructions = f"""
   - Make sure the delivery address is set to: {DELIVERY_ADDRESS}
   - Phone number: {DELIVERY_PHONE}"""

    browser_task = f"""You are an AI agent helping a user in {USER_LOCATION} order groceries.

Task: Order the following ingredients from {store_url} for making {dish_name}:
{ingredients_list}

Steps:
1. Go to {store_url}{login_instructions}
3. Search for and add each ingredient to the cart (pick the most affordable/relevant option)
4. Go to cart and verify all items{address_instructions}
5. Complete the checkout and place the order
6. Report the order confirmation number and total price

Important:
- If an item is not available, skip it and note it as unavailable
- Pick the smallest/most affordable pack size
- Complete the full checkout including payment
- Report back with: items ordered, items unavailable, total cost, order ID"""

    # ── Step 3: Launch browser task ──
    print("🌐 Step 2: Launching Browser Use via Locus...")
    try:
        task_id = run_browser_task(browser_task, max_steps=150)

        if not task_id:
            raise Exception("No task ID returned from Browser Use — check API response above")

        print(f"  ✅ Task started — ID: {task_id}\n")

        # ── Step 4: Poll for result ──
        result = wait_for_task(task_id, timeout=300)

        if "error" in result and not result.get("output"):
            order_result = f"⚠️ Browser task issue: {result.get('error', 'Unknown')}\n\nRaw result: {str(result)[:500]}"
            order_status = "failed"
        else:
            output = (
                result.get("output") or
                result.get("result") or
                result.get("final_result") or
                str(result)
            )
            order_result = f"🏪 Store: {store_url}\n\n{output}"
            order_status = "completed"

    except Exception as e:
        order_result = f"❌ Error during ordering: {str(e)}"
        order_status = "error"
        print(order_result)

    # ── Step 5: Display ──
    print("=" * 55)
    print("🛒  ORDER AGENT OUTPUT")
    print("=" * 55)
    print(order_result)
    print("=" * 55 + "\n")

    return {
        **state,
        "order_status": order_status,
        "order_result": order_result,
        "selected_store": store_url,
        "next_action": "end"
    }