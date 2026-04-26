import streamlit as st
import requests
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from nutrition_agent import nutrition_agent_node
from recipe_agent import recipe_agent_node
from order_agent import order_agent_node

# ─────────────────────────────────────────────
# Page Config
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="🥗 Dietary Assistant",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
    .main-header {
        background: linear-gradient(135deg, #065f46, #10b981);
        padding: 2rem; border-radius: 16px;
        margin-bottom: 2rem; text-align: center; color: white;
    }
    .main-header h1 { font-size: 2.5rem; margin: 0; }
    .main-header p  { font-size: 1rem; opacity: 0.85; margin: 0.3rem 0 0 0; }
    .result-card {
        background: #f0fdf4; border: 1px solid #bbf7d0;
        border-radius: 12px; padding: 1.2rem; margin-bottom: 1rem;
    }
    .missing-card {
        background: #fff7ed; border: 1px solid #fed7aa;
        border-radius: 12px; padding: 1.2rem; margin-bottom: 1rem;
    }
    .order-card {
        background: #eff6ff; border: 1px solid #bfdbfe;
        border-radius: 12px; padding: 1.2rem; margin-bottom: 1rem;
    }
    .youtube-card {
        background: #fff1f2; border: 1px solid #fecdd3;
        border-radius: 12px; padding: 1.2rem; margin-bottom: 1rem;
    }
    .pantry-item { padding: 0.4rem 0.8rem; border-radius: 8px; margin: 0.2rem 0; font-size: 0.95rem; }
    .pantry-available { background: #dcfce7; color: #166534; }
    .pantry-unavailable { background: #fee2e2; color: #991b1b; }
    .step-badge {
        background: #10b981; color: white; border-radius: 50%;
        width: 28px; height: 28px; display: inline-flex;
        align-items: center; justify-content: center; font-weight: 700;
        margin-right: 8px; font-size: 0.85rem;
    }
    footer { display: none !important; }
    div[data-testid="stSidebarNav"] { display: none; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Session State Init
# ─────────────────────────────────────────────

if "medical_profile" not in st.session_state:
    st.session_state.medical_profile = {
        "conditions": [], "allergies": [],
        "doctor_notes": [], "last_updated": None
    }
if "pantry" not in st.session_state:
    st.session_state.pantry = []
if "last_result" not in st.session_state:
    st.session_state.last_result = None

# ─────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────

st.sidebar.markdown("## 🥗 Dietary Assistant")
st.sidebar.markdown("*Powered by Locus + Gemini + Serper*")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigate",
    ["🍽️ Food Request", "🏥 Medical Profile", "📦 Pantry Tracker"],
    label_visibility="collapsed"
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 Your Profile")
conditions = st.session_state.medical_profile["conditions"]
allergies  = st.session_state.medical_profile["allergies"]
pantry     = st.session_state.pantry
available  = [i for i in pantry if i["available"]]

st.sidebar.markdown(f"🏥 **Conditions:** {', '.join(conditions) if conditions else 'None'}")
st.sidebar.markdown(f"⚠️ **Allergies:** {', '.join(allergies) if allergies else 'None'}")
st.sidebar.markdown(f"📦 **Pantry:** {len(available)} item(s) available")
st.sidebar.markdown(f"📍 **Location:** {os.getenv('USER_LOCATION', 'Not set')}")


# ─────────────────────────────────────────────
# PAGE 1: Food Request
# ─────────────────────────────────────────────

if page == "🍽️ Food Request":
    st.markdown("""
    <div class="main-header">
        <h1>🍽️ Food Request</h1>
        <p>Tell me what you want — I'll find the best dish, recipe, and order the ingredients!</p>
    </div>
    """, unsafe_allow_html=True)

    food_input = st.text_area(
        "What are you craving?",
        placeholder="e.g. Something light and healthy, maybe Indian food...",
        height=100
    )

    col1, col2 = st.columns([1, 4])
    with col1:
        search_btn = st.button("🔍 Find Best Options", type="primary", use_container_width=True)

    if search_btn:
        if not food_input.strip():
            st.warning("⚠️ Please enter what you'd like to eat.")
        else:
            agent_state = {
                "messages": [],
                "food_request": food_input,
                "medical_profile": st.session_state.medical_profile,
                "pantry": st.session_state.pantry,
                "recommendations": None,
                "missing_ingredients": None,
                "recipe": None,
                "dish_name": None,
                "youtube_video": None,
                "order_status": None,
                "order_result": None,
                "selected_store": None,
                "nutrition_info": None,
                "current_mode": "food_request",
                "next_action": "nutrition_agent",
            }

            available_items = [i["name"] for i in st.session_state.pantry if i["available"]]
            with st.expander("📋 Intake Summary", expanded=True):
                col_a, col_b, col_c, col_d = st.columns(4)
                col_a.metric("Request", food_input[:30] + "..." if len(food_input) > 30 else food_input)
                col_b.metric("Conditions", len(conditions))
                col_c.metric("Allergies", len(allergies))
                col_d.metric("Pantry Items", len(available_items))

            # ── Run agents sequentially with progress ──
            progress = st.progress(0, text="Starting agents...")

            try:
                # Step 1: Nutrition Agent
                progress.progress(10, text="🥦 Running Nutrition Agent — searching web...")
                with st.spinner("🥦 Nutrition Agent: Searching Serper + analysing with Gemini..."):
                    result = nutrition_agent_node(agent_state)
                    agent_state.update(result)
                progress.progress(40, text="✅ Nutrition Agent done!")

                # Step 2: Recipe Agent
                progress.progress(45, text="🍳 Running Recipe Agent — finding recipe + YouTube...")
                with st.spinner("🍳 Recipe Agent: Finding recipe and YouTube video..."):
                    result = recipe_agent_node(agent_state)
                    agent_state.update(result)
                progress.progress(70, text="✅ Recipe Agent done!")

                # Step 3: Order Agent
                progress.progress(75, text="🛒 Running Order Agent — browsing grocery store...")
                with st.spinner("🛒 Order Agent: Finding best store and adding items to cart..."):
                    result = order_agent_node(agent_state)
                    agent_state.update(result)
                progress.progress(100, text="✅ All done!")

                st.session_state.last_result = agent_state
                st.success("🎉 All agents completed! Scroll down to see your results.")

            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                st.stop()

    # ── Show Results ──
    if st.session_state.last_result:
        r = st.session_state.last_result

        st.markdown("---")
        st.markdown("## 📊 Results")

        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🥗 Recommendation",
            "🍳 Recipe",
            "📺 YouTube",
            "🛒 Order Status",
            "🔗 Sources"
        ])

        with tab1:
            st.markdown('<div class="result-card">', unsafe_allow_html=True)
            st.markdown(r.get("recommendations", "No recommendation generated."))
            st.markdown('</div>', unsafe_allow_html=True)

            missing = r.get("missing_ingredients", [])
            if missing:
                st.markdown('<div class="missing-card">', unsafe_allow_html=True)
                st.markdown("### 🛒 Missing Ingredients")
                for item in missing:
                    st.markdown(f"- 🛒 **{item}**")
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.success("✅ Your pantry has everything you need!")

        with tab2:
            recipe = r.get("recipe", "")
            if recipe:
                st.markdown('<div class="result-card">', unsafe_allow_html=True)
                st.markdown(recipe)
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.info("No recipe generated yet.")

        with tab3:
            video = r.get("youtube_video")
            if video:
                st.markdown('<div class="youtube-card">', unsafe_allow_html=True)
                st.markdown("### 📺 Recommended YouTube Video")
                st.markdown(f"**{video.get('title', '')}**")
                st.markdown(f"📺 Channel: {video.get('channel', '')}")
                st.markdown(f"⏱️ Duration: {video.get('duration', 'N/A')}")
                st.markdown(f"🔗 [Watch on YouTube]({video.get('link', '')})")
                st.markdown('</div>', unsafe_allow_html=True)

                # Embed YouTube video if possible
                link = video.get("link", "")
                if "youtube.com/watch?v=" in link:
                    video_id = link.split("v=")[-1].split("&")[0]
                    st.video(f"https://www.youtube.com/watch?v={video_id}")
            else:
                st.info("No YouTube video found.")

        with tab4:
            order_status = r.get("order_status", "")
            order_result = r.get("order_result", "")
            store = r.get("selected_store", "")

            if order_status == "nothing_to_order":
                st.success("✅ Nothing to order — pantry is fully stocked!")
            elif order_status == "completed":
                st.success(f"✅ Order placed successfully via {store}")
                st.markdown('<div class="order-card">', unsafe_allow_html=True)
                st.markdown(order_result)
                st.markdown('</div>', unsafe_allow_html=True)
            elif order_status in ["failed", "error"]:
                st.warning(f"⚠️ Order attempt encountered an issue:")
                st.markdown('<div class="order-card">', unsafe_allow_html=True)
                st.markdown(order_result)
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.info("Order status not available.")

        with tab5:
            st.markdown("### 🔗 Search Sources")
            st.markdown("*Results fetched via Serper (Google Search)*")
            nutrition_info = r.get("nutrition_info", "")
            if nutrition_info:
                for line in nutrition_info.split("\n")[:12]:
                    if line.strip():
                        st.markdown(f"• {line.strip()}")


# ─────────────────────────────────────────────
# PAGE 2: Medical Profile
# ─────────────────────────────────────────────

elif page == "🏥 Medical Profile":
    st.markdown("""
    <div class="main-header">
        <h1>🏥 Medical Profile</h1>
        <p>Keep your health info updated for personalised recommendations</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### ➕ Add Health Condition")
        condition_input = st.text_input("Condition", placeholder="e.g. Arthritis, Diabetes...")
        if st.button("Add Condition", type="primary"):
            if condition_input.strip():
                st.session_state.medical_profile["conditions"].append(condition_input.strip())
                st.session_state.medical_profile["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                st.success(f"✅ Added: {condition_input.strip()}")
                st.rerun()
            else:
                st.warning("⚠️ Please enter a condition.")

        st.markdown("### ➕ Add Allergy")
        allergy_input = st.text_input("Allergy", placeholder="e.g. Peanuts, Gluten...")
        if st.button("Add Allergy", type="primary"):
            if allergy_input.strip():
                st.session_state.medical_profile["allergies"].append(allergy_input.strip())
                st.session_state.medical_profile["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                st.success(f"✅ Added: {allergy_input.strip()}")
                st.rerun()
            else:
                st.warning("⚠️ Please enter an allergy.")

        st.markdown("### 📄 Paste Doctor Notes")
        notes_input = st.text_area("Doctor Report", placeholder="Paste your doctor's notes here...", height=150)
        if st.button("💾 Save & Extract with AI", type="primary"):
            if notes_input.strip():
                LOCUS_API_KEY = os.getenv("LOCUS_API_KEY")
                headers = {
                    "Authorization": f"Bearer {LOCUS_API_KEY}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": "gemini-2.5-flash",
                    "messages": [{"role": "user", "content": f"Doctor notes: {notes_input}"}],
                    "systemInstruction": "You are a medical data extractor. Extract health conditions, allergies, medications, or dietary restrictions. Return a brief structured summary.",
                    "temperature": 0.5,
                    "maxOutputTokens": 512
                }
                with st.spinner("🤖 Extracting key info via Gemini (Locus)..."):
                    try:
                        resp = requests.post(
                            "https://beta-api.paywithlocus.com/api/wrapped/gemini/chat",
                            headers=headers, json=payload, timeout=30
                        )
                        summary = resp.json()["data"]["candidates"][0]["content"]["parts"][0]["text"]
                        st.session_state.medical_profile["doctor_notes"].append(
                            f"[{datetime.now().strftime('%Y-%m-%d')}] {notes_input}"
                        )
                        st.session_state.medical_profile["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                        st.success("✅ Notes saved!")
                        st.info(f"🤖 Extracted:\n{summary}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
            else:
                st.warning("⚠️ Please paste some notes.")

    with col2:
        st.markdown("### 📊 Current Profile")
        profile = st.session_state.medical_profile

        st.markdown("**🏥 Health Conditions:**")
        if profile["conditions"]:
            for c in profile["conditions"]:
                st.markdown(f"- {c}")
        else:
            st.markdown("*None added yet*")

        st.markdown("**⚠️ Allergies:**")
        if profile["allergies"]:
            for a in profile["allergies"]:
                st.markdown(f"- {a}")
        else:
            st.markdown("*None added yet*")

        st.markdown(f"**📋 Doctor Notes:** {len(profile['doctor_notes'])} note(s) saved")
        st.markdown(f"**🕐 Last Updated:** {profile['last_updated'] or 'Never'}")

        st.markdown("---")
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🗑️ Clear Conditions", use_container_width=True):
                st.session_state.medical_profile["conditions"] = []
                st.session_state.medical_profile["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                st.rerun()
        with col_b:
            if st.button("🗑️ Clear Allergies", use_container_width=True):
                st.session_state.medical_profile["allergies"] = []
                st.session_state.medical_profile["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                st.rerun()


# ─────────────────────────────────────────────
# PAGE 3: Pantry Tracker
# ─────────────────────────────────────────────

elif page == "📦 Pantry Tracker":
    st.markdown("""
    <div class="main-header">
        <h1>📦 Pantry Tracker</h1>
        <p>Track what's at home — the AI uses this to minimise what needs to be ordered</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### ➕ Add Item")
        pantry_input = st.text_input("Item Name", placeholder="e.g. Tomatoes, Olive Oil...")
        if st.button("Add to Pantry", type="primary", use_container_width=True):
            if pantry_input.strip():
                name = pantry_input.strip()
                existing = next(
                    (i for i, x in enumerate(st.session_state.pantry)
                     if x["name"].lower() == name.lower()), None
                )
                if existing is not None:
                    st.session_state.pantry[existing]["available"] = True
                    st.success(f"✅ '{name}' marked as available.")
                else:
                    st.session_state.pantry.append({"name": name, "available": True})
                    st.success(f"✅ Added '{name}'.")
                st.rerun()
            else:
                st.warning("⚠️ Please enter an item name.")

        st.markdown("### 🔄 Update Item")
        update_input = st.text_input("Item to Update", placeholder="e.g. Tomatoes...")
        col_a, col_b = st.columns(2)

        with col_a:
            if st.button("❌ Mark Used Up", use_container_width=True):
                if update_input.strip():
                    name = update_input.strip()
                    found = next(
                        (i for i, x in enumerate(st.session_state.pantry)
                         if x["name"].lower() == name.lower()), None
                    )
                    if found is not None:
                        st.session_state.pantry[found]["available"] = False
                        st.success(f"❌ '{name}' marked as used up.")
                        st.rerun()
                    else:
                        st.warning(f"'{name}' not found.")

        with col_b:
            if st.button("✅ Restocked", use_container_width=True):
                if update_input.strip():
                    name = update_input.strip()
                    found = next(
                        (i for i, x in enumerate(st.session_state.pantry)
                         if x["name"].lower() == name.lower()), None
                    )
                    if found is not None:
                        st.session_state.pantry[found]["available"] = True
                    else:
                        st.session_state.pantry.append({"name": name, "available": True})
                    st.success(f"✅ '{name}' restocked.")
                    st.rerun()

        if st.button("🗑️ Clear All Pantry", use_container_width=True):
            st.session_state.pantry = []
            st.rerun()

    with col2:
        st.markdown("### 📋 Your Pantry")
        pantry = st.session_state.pantry

        if not pantry:
            st.info("No items yet. Add some on the left!")
        else:
            available_items   = [i for i in pantry if i["available"]]
            unavailable_items = [i for i in pantry if not i["available"]]

            if available_items:
                st.markdown("**✅ Available:**")
                for item in available_items:
                    st.markdown(
                        f'<div class="pantry-item pantry-available">✅ {item["name"]}</div>',
                        unsafe_allow_html=True
                    )

            if unavailable_items:
                st.markdown("**❌ Used Up:**")
                for item in unavailable_items:
                    st.markdown(
                        f'<div class="pantry-item pantry-unavailable">❌ {item["name"]}</div>',
                        unsafe_allow_html=True
                    )

            st.markdown("---")
            st.markdown(
                f"**Total:** {len(pantry)} items | "
                f"✅ {len(available_items)} available | "
                f"❌ {len(unavailable_items)} used up"
            )