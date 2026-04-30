import os
import time
import json
import requests
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from browserbase import Browserbase
from state import AgentState

load_dotenv()

LOCUS_API_KEY       = os.getenv("LOCUS_API_KEY")
USER_LOCATION       = os.getenv("USER_LOCATION", "Bengaluru, Karnataka, India")
DELIVERY_ADDRESS    = os.getenv("DELIVERY_ADDRESS", "")
DELIVERY_PHONE      = os.getenv("DELIVERY_PHONE", "")
BLINKIT_COOKIES     = os.getenv("BLINKIT_COOKIES", "")
ZEPTO_COOKIES       = os.getenv("ZEPTO_COOKIES", "")
BROWSERBASE_API_KEY = os.getenv("BROWSERBASE_API_KEY", "")
BROWSERBASE_PROJECT_ID = os.getenv("BROWSERBASE_PROJECT_ID", "")

GEMINI_URL = "https://beta-api.paywithlocus.com/api/wrapped/gemini/chat"
LOCUS_HEADERS = {
    "Authorization": f"Bearer {LOCUS_API_KEY}",
    "Content-Type": "application/json"
}

# ─────────────────────────────────────────────
# Store configs
# ─────────────────────────────────────────────

STORES = [
    {
        "name": "Blinkit",
        "url": "https://www.blinkit.com",
        "cookies": BLINKIT_COOKIES,
        "domain": ".blinkit.com",
        "search_selector": 'input[placeholder*="Search"], input[type="search"]',
        "add_btn_selector": 'button[class*="AddToCart"], div[class*="add-to-cart"], button:has-text("ADD")',
        "cart_selector": 'a[href*="cart"], div[class*="cart-icon"], button[class*="cart"]',
        "checkout_selector": 'button:has-text("Proceed"), button:has-text("Checkout")',
        "cod_selector": 'text=Cash on Delivery, label:has-text("Cash"), input[value*="cod"]',
        "place_order_selector": 'button:has-text("Place Order"), button:has-text("Confirm")'
    },
    {
        "name": "Zepto",
        "url": "https://www.zeptonow.com",
        "cookies": ZEPTO_COOKIES,
        "domain": ".zeptonow.com",
        "search_selector": 'input[placeholder*="Search"], input[type="search"]',
        "add_btn_selector": 'button[class*="add"], div[class*="AddButton"], button:has-text("+")',
        "cart_selector": 'a[href*="cart"], div[class*="CartIcon"], button[class*="cart"]',
        "checkout_selector": 'button:has-text("Proceed"), button:has-text("Checkout")',
        "cod_selector": 'text=Cash on Delivery, label:has-text("Cash"), input[value*="cod"]',
        "place_order_selector": 'button:has-text("Place Order"), button:has-text("Confirm")'
    }
]


# ─────────────────────────────────────────────
# Cookie parser
# ─────────────────────────────────────────────

def parse_cookies(cookie_str: str, domain: str, url: str) -> list:
    """Parse cookie string into Playwright format."""
    cookies = []
    for cookie in cookie_str.split(";"):
        cookie = cookie.strip()
        if "=" in cookie:
            name, value = cookie.split("=", 1)
            # Playwright requires EITHER url OR domain, not both
            cookies.append({
                "name": name.strip(),
                "value": value.strip(),
                "url": url,
            })
    return cookies


# ─────────────────────────────────────────────
# Order via Browserbase + Playwright
# ─────────────────────────────────────────────

def order_via_browserbase(store: dict, ingredients: list, dish_name: str) -> tuple[bool, str]:
    """
    Creates a Browserbase session, connects via Playwright,
    injects cookies natively, then places a COD order.
    """
    print(f"\n  🏪 Trying {store['name']} via Browserbase + Playwright...")

    if not store["cookies"]:
        return False, f"No cookies for {store['name']}"

    bb = Browserbase(api_key=BROWSERBASE_API_KEY)
    results = {
        "ordered": [],
        "not_found": [],
        "total": "",
        "order_id": "",
        "delivery_time": "",
        "error": ""
    }

    try:
        # Step 1: Create Browserbase session
        print("  🌐 Creating Browserbase session...")
        session = bb.sessions.create(project_id=BROWSERBASE_PROJECT_ID)
        session_id = session.id
        print(f"  ✅ Session: {session_id}")
        print(f"  👀 Watch live: https://browserbase.com/sessions/{session_id}")

        with sync_playwright() as playwright:
            # Step 2: Connect via CDP
            browser = playwright.chromium.connect_over_cdp(session.connect_url)
            context = browser.contexts[0]
            page = context.pages[0]

            # Step 3: Navigate to store first (needed before setting cookies)
            print(f"  🌐 Navigating to {store['url']}...")
            page.goto(store["url"], wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)

            # Step 4: Inject cookies via Playwright's native add_cookies
            print(f"  🍪 Injecting cookies via Playwright...")
            cookies = parse_cookies(store["cookies"], store["domain"], store["url"])
            context.add_cookies(cookies)
            print(f"  ✅ {len(cookies)} cookies injected")

            # Step 5: Reload to apply cookies
            page.reload(wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(3000)
            print(f"  📄 Page title: {page.title()}")

            # Step 6: Verify logged in
            page_text = page.evaluate("document.body.innerText")
            is_logged_in = any(word in page_text.lower() for word in [
                "logout", "my account", "profile", "orders", DELIVERY_ADDRESS.split(",")[0].lower()
            ])
            print(f"  {'✅ Logged in!' if is_logged_in else '⚠️ May not be logged in — continuing anyway...'}")

            # Step 7: Search and add each ingredient
            for item in ingredients:
                try:
                    print(f"  🔍 Searching for: {item}")

                    # Click search
                    search = page.locator(store["search_selector"]).first
                    search.click()
                    page.wait_for_timeout(500)
                    search.fill("")
                    search.type(item, delay=80)
                    page.wait_for_timeout(2500)

                    # Try to click add button
                    add_btn = page.locator(store["add_btn_selector"]).first
                    if add_btn.is_visible(timeout=3000):
                        add_btn.click()
                        page.wait_for_timeout(1000)
                        results["ordered"].append(item)
                        print(f"  ✅ Added: {item}")
                    else:
                        results["not_found"].append(item)
                        print(f"  ❌ Not found: {item}")

                except Exception as e:
                    results["not_found"].append(item)
                    print(f"  ❌ Error adding {item}: {str(e)[:80]}")

            # Step 8: Go to cart
            print("  🛒 Going to cart...")
            try:
                cart_btn = page.locator(store["cart_selector"]).first
                if cart_btn.is_visible(timeout=3000):
                    cart_btn.click()
                else:
                    page.goto(f"{store['url']}/cart", wait_until="domcontentloaded")
                page.wait_for_timeout(2000)
            except:
                page.goto(f"{store['url']}/cart", wait_until="domcontentloaded")
                page.wait_for_timeout(2000)

            # Step 9: Proceed to checkout
            print("  💳 Proceeding to checkout...")
            try:
                checkout_btn = page.locator(store["checkout_selector"]).first
                if checkout_btn.is_visible(timeout=3000):
                    checkout_btn.click()
                    page.wait_for_timeout(2000)
            except Exception as e:
                print(f"  ⚠️ Checkout button: {str(e)[:60]}")

            # Step 10: Select Cash on Delivery
            print("  💵 Selecting Cash on Delivery...")
            try:
                cod = page.locator(store["cod_selector"]).first
                if cod.is_visible(timeout=3000):
                    cod.click()
                    page.wait_for_timeout(1000)
                    print("  ✅ COD selected")
                else:
                    print("  ⚠️ COD option not visible")
            except Exception as e:
                print(f"  ⚠️ COD selection: {str(e)[:60]}")

            # Step 11: Place order
            print("  📦 Placing order...")
            try:
                place_btn = page.locator(store["place_order_selector"]).first
                if place_btn.is_visible(timeout=3000):
                    place_btn.click()
                    page.wait_for_timeout(4000)
                    print("  ✅ Order placed!")
            except Exception as e:
                print(f"  ⚠️ Place order: {str(e)[:60]}")

            # Step 12: Get confirmation
            page_text = page.evaluate("document.body.innerText")

            order_match = None
            for pattern in ["Order #", "Order ID", "order id", "#ORD", "ORD-"]:
                idx = page_text.upper().find(pattern.upper())
                if idx != -1:
                    order_match = page_text[idx:idx+30].strip()
                    break

            total_match = None
            import re
            total_found = re.findall(r'[₹$]\s*[\d,]+', page_text)
            if total_found:
                total_match = total_found[0]

            results["order_id"] = order_match or "Check your app for order ID"
            results["total"] = total_match or "Check your app for total"

            browser.close()

        # Build result summary
        success = bool(results["ordered"]) and (
            results["order_id"] != "Check your app for order ID" or
            len(results["ordered"]) > 0
        )

        summary = (
            f"🏪 Store: {store['name']}\n"
            f"📍 Address: {DELIVERY_ADDRESS}\n\n"
            f"✅ Added to cart: {', '.join(results['ordered']) if results['ordered'] else 'None'}\n"
            f"❌ Not found: {', '.join(results['not_found']) if results['not_found'] else 'None'}\n"
            f"💰 Total: {results['total']}\n"
            f"📦 Order ID: {results['order_id']}\n"
            f"👀 Session replay: https://browserbase.com/sessions/{session_id}"
        )

        return success, summary

    except Exception as e:
        error = f"❌ Browserbase error on {store['name']}: {str(e)}"
        print(f"  {error}")
        return False, error


# ─────────────────────────────────────────────
# Order Agent Node
# ─────────────────────────────────────────────

def order_agent_node(state: AgentState) -> AgentState:
    print("\n🛒  [Order Agent] Starting grocery ordering via Browserbase...\n")

    missing_ingredients = state.get("missing_ingredients", [])
    dish_name = state.get("dish_name", "the recommended dish")

    if not missing_ingredients:
        return {
            **state,
            "order_status": "nothing_to_order",
            "order_result": "✅ All ingredients already in pantry!",
            "next_action": "end"
        }

    active_stores = [s for s in STORES if s["cookies"]]

    print(f"  📍 Location  : {USER_LOCATION}")
    print(f"  🏠 Address   : {DELIVERY_ADDRESS}")
    print(f"  🍽️  Dish      : {dish_name}")
    print(f"  🛒 Items     : {', '.join(missing_ingredients)}")
    print(f"  🏪 Stores    : {' → '.join([s['name'] for s in active_stores])}\n")

    order_status = "failed"
    order_result = ""
    selected_store = ""

    for store in active_stores:
        success, result = order_via_browserbase(store, missing_ingredients, dish_name)
        order_result = result
        selected_store = store["url"]

        if success:
            order_status = "completed"
            print(f"\n  🎉 Order placed on {store['name']}!")
            break
        else:
            print(f"\n  ⚠️  {store['name']} incomplete — trying next...")
            order_result += "\n\n⚠️ Trying next store..."

    if order_status == "failed":
        order_result += "\n\n❌ Could not complete order on any store."

    print("\n" + "=" * 55)
    print("🛒  ORDER AGENT OUTPUT")
    print("=" * 55)
    print(order_result)
    print("=" * 55 + "\n")

    return {
        **state,
        "order_status": order_status,
        "order_result": order_result,
        "selected_store": selected_store,
        "next_action": "end"
    }