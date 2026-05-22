"""Streamlit Frontend — Modern UI for the Multi-Agent AI Travel Planner."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import streamlit as st

# ── Page config ──────────────────────────────
st.set_page_config(
    page_title="AI Travel Planner",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom CSS ───────────────────────────────
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .stTextArea textarea { font-size: 15px; }
    .plan-box {
        background: #1a1d27; border: 1px solid #2d3148;
        border-radius: 12px; padding: 20px; margin: 10px 0;
        color: #e0e0e0; line-height: 1.7;
    }
    .metric-card {
        background: linear-gradient(135deg, #1e2235, #252840);
        border: 1px solid #3d4266; border-radius: 10px;
        padding: 15px; text-align: center;
    }
    .tag { background: #2d3561; color: #7b8cde;
           padding: 3px 10px; border-radius: 20px;
           font-size: 12px; margin: 2px; display: inline-block; }
    .section-header { color: #7b8cde; font-size: 18px;
                      font-weight: 700; margin: 15px 0 8px 0; }
    div[data-testid="stExpander"] { border: 1px solid #2d3148 !important;
                                    border-radius: 10px !important; }
</style>
""", unsafe_allow_html=True)

# ── Import backend ───────────────────────────
from graph.workflow import travel_graph, refinement_graph, TravelState
from agents.rewards_agent import rewards_to_text
from agents.planner_agent import itinerary_to_text
from agents.validator_agent import clean_itinerary

# ── Session State ────────────────────────────
for key in ["trip_state", "itinerary_generated", "final_state"]:
    if key not in st.session_state:
        st.session_state[key] = None
if "itinerary_generated" not in st.session_state:
    st.session_state.itinerary_generated = False

# ── Sidebar ───────────────────────────────────
with st.sidebar:
    st.markdown("## ✈️ AI Travel Planner")
    st.markdown("*Multi-Agent • Memory-Powered*")
    st.divider()
    user_id = st.text_input("👤 Your User ID", value="traveller_01", help="Unique ID — memory is per-user")
    st.divider()
    st.markdown("**How it works:**")
    st.markdown("""
    1. Enter your travel query
    2. The scheduler builds a destination-locked plan
    3. Refine with natural language
    4. Get rewards & budget tips
    """)

# ── Main Header ───────────────────────────────
st.markdown("# ✈️ Multi-Agent AI Travel Planner")
st.markdown("*Powered by LangGraph • ChromaDB Memory • RAG • Reward Optimization*")
st.divider()

# ── STEP 1: Query Input ───────────────────────
st.markdown("### 🗺️ Step 1 — Tell us about your trip")

example_queries = [
    "3-day Manali trip under ₹20,000. Have SBI and HDFC cards. Like scenic places, local food, relaxed travel.",
    "Plan 4-day Goa trip for ₹25,000. Have HDFC Millennia card. Love beaches, seafood, and sunset views.",
    "5-day Jaipur heritage trip under ₹30,000. Like history, local bazaars, and authentic Rajasthani food."
]

col1, col2 = st.columns([3, 1])
with col1:
    user_query = st.text_area(
        "Describe your dream trip:",
        placeholder="e.g. I want a 3-day Manali trip under ₹20,000. I have SBI and HDFC cards. I like scenic places, local food, and relaxed travel.",
        height=100
    )
with col2:
    st.markdown("**💡 Quick Examples:**")
    for i, ex in enumerate(example_queries):
        if st.button(f"Example {i+1}", key=f"ex_{i}"):
            st.session_state["prefill_query"] = ex

if "prefill_query" in st.session_state:
    user_query = st.session_state.prefill_query

generate_btn = st.button("🚀 Generate My Trip Plan", type="primary", use_container_width=True)

# ── STEP 2: Generate Trip ─────────────────────
if generate_btn and user_query.strip():
    with st.spinner("🤖 Agents working... Parsing query → Retrieving memory → Planning itinerary → Budget & Rewards..."):
        initial_state: TravelState = {
            "user_id": user_id,
            "raw_query": user_query,
            "destination": "",
            "structured_query": {},
            "rag_context": "",
            "rag_documents": [],
            "allowed_places": [],
            "allowed_place_entities": [],
            "itinerary_json": {},
            "itinerary": "",
            "refined_itinerary_json": {},
            "refined_itinerary": "",
            "budget": {},
            "rewards": {},
            "summary": "",
            "user_feedback": None,
            "memory_context": "",
            "behavior_profile": {},
            "session_memory": {},
            "validation_report": {},
            "modification_intent": {},
            "changed_days": [],
            "stored_memories": [],
            "status": "started"
        }
        try:
            result = travel_graph.invoke(initial_state)
            st.session_state.trip_state = result
            st.session_state.itinerary_generated = True
            st.session_state.final_state = result
            st.success("✅ Trip plan generated successfully!")
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")

# ── STEP 3: Display Results ───────────────────
if st.session_state.itinerary_generated and st.session_state.trip_state:
    state = st.session_state.trip_state
    sq = state.get("structured_query", {})

    st.divider()
    
    st.markdown("### Trip Profile")
    cols = st.columns(5)
    tags = [
        ("📍", sq.get("destination", "N/A")),
        ("📅", f"{sq.get('days', 'N/A')} Days"),
        ("💰", f"₹{sq.get('budget', 'N/A')}"),
        ("🚶", sq.get("travel_pace", "N/A")),
        ("🍽️", sq.get("food_preference", "N/A")),
    ]
    for col, (icon, val) in zip(cols, tags):
        with col:
            st.metric(icon, val)

    st.divider()

    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 Itinerary", "✏️ Refine", "💰 Budget", "💳 Rewards", "📝 Summary"])

    # ── Tab 1: Itinerary
    with tab1:
        st.markdown("### Itinerary")
        clean_plan = clean_itinerary(
            state.get("refined_itinerary_json") or state.get("itinerary_json", {}),
            sq.get("destination", state.get("destination", "")),
        )
        itinerary_text = itinerary_to_text(clean_plan)
        st.markdown(f"<div class='plan-box'>{itinerary_text.replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)

    # ── Tab 2: Refinement
    with tab2:
        st.markdown("### ✏️ Refine Your Itinerary")
        st.markdown("Tell the AI what to change in plain English:")
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**💡 Try saying:**")
            suggestions = ["add Kullu also", "avoid Rohtang Pass", "add more cafes", 
                          "less hectic schedule", "add local market", "more budget options"]
            for s in suggestions:
                if st.button(f'"{s}"', key=f"sug_{s}"):
                    st.session_state["feedback_text"] = s

        feedback = st.text_input(
            "Your modification:",
            value=st.session_state.get("feedback_text", ""),
            placeholder="e.g. add Kullu also, remove Rohtang Pass, more relaxed pacing..."
        )
        
        if st.button("🔄 Apply Refinement", type="primary"):
            if feedback.strip():
                with st.spinner("🤖 Refining your itinerary..."):
                    refine_input = {**state, "user_feedback": feedback}
                    try:
                        refined = refinement_graph.invoke(refine_input)
                        st.session_state.trip_state = refined
                        st.session_state.final_state = refined
                        st.success("✅ Itinerary updated!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

    # ── Tab 3: Budget
    with tab3:
        st.markdown("### 💰 Budget Breakdown")
        budget = state.get("budget", {})
        if budget and "grand_total" in budget:
            cols = st.columns(4)
            metrics = [
                ("🏨 Stay", f"₹{budget.get('accommodation', {}).get('total', 'N/A')}"),
                ("🍽️ Food", f"₹{budget.get('food', {}).get('total', 'N/A')}"),
                ("🚌 Transport", f"₹{budget.get('transport', {}).get('total', 'N/A')}"),
                ("🎭 Activities", f"₹{budget.get('activities', {}).get('total', 'N/A')}"),
            ]
            for col, (label, val) in zip(cols, metrics):
                with col:
                    st.metric(label, val)
            
            st.divider()
            col1, col2, col3 = st.columns(3)
            col1.metric("💰 Grand Total", f"₹{budget.get('grand_total', 'N/A')}")
            col2.metric("📅 Per Day Avg", f"₹{budget.get('per_day_average', 'N/A')}")
            status = budget.get("budget_status", "N/A")
            col3.metric("📊 Budget Status", status)
            
            if budget.get("savings_tips"):
                st.markdown("**💡 Savings Tips:**")
                for tip in budget["savings_tips"]:
                    st.markdown(f"• {tip}")
        else:
            st.info("Budget data not available. Generate a trip first.")

    # ── Tab 4: Rewards
    with tab4:
        st.markdown("### 💳 Credit Card & Reward Optimization")
        rewards = state.get("rewards", "")
        rewards_text = rewards_to_text(rewards) if isinstance(rewards, dict) else rewards
        if rewards_text:
            st.markdown(f"<div class='plan-box'>{rewards_text.replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)
        else:
            st.info("No reward data yet.")

    # ── Tab 5: Summary
    with tab5:
        st.markdown("### 📝 Your Personal Trip Summary")
        summary = state.get("summary", "")
        if summary:
            st.markdown(f"<div class='plan-box'>{summary.replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)
            
            # Download
            full_data = {
                "trip_profile": sq,
                "itinerary": itinerary_to_text(clean_itinerary(state.get("refined_itinerary_json") or state.get("itinerary_json", {}), sq.get("destination", ""))),
                "itinerary_json": clean_itinerary(state.get("refined_itinerary_json") or state.get("itinerary_json", {}), sq.get("destination", "")),
                "budget": state.get("budget"),
                "rewards": state.get("rewards"),
                "summary": summary
            }
            st.download_button(
                "💾 Download Full Trip Plan (JSON)",
                data=json.dumps(full_data, indent=2),
                file_name=f"trip_{sq.get('destination', 'plan').lower()}_{sq.get('days', '')}days.json",
                mime="application/json"
            )

elif not st.session_state.itinerary_generated:
    st.markdown("""
    <div style='text-align:center; padding: 60px; color: #555;'>
        <h2>🌍 Ready to plan your perfect trip?</h2>
        <p>Enter your travel query above and let the AI agents do the magic!</p>
        <p style='font-size:13px'>Powered by GPT-4o-mini • LangGraph • ChromaDB • RAG</p>
    </div>
    """, unsafe_allow_html=True)
