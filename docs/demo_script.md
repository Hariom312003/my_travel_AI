# Product Demonstration Guide

This guide details two scenarios for demonstrating **my_travel_AI**'s capabilities to recruiters, engineers, or academic reviewers.

---

## Scenario A: One-Click Demo Mode (Fast Sandbox)

This is the fastest way to showcase memory isolation and multi-agent execution.

### Steps
1. Navigate to the **🏠 Product Home & Sandbox** tab.
2. Scroll to the **One-Click Demo Sandbox** card.
3. Click the **Execute Sandbox Simulation** button.

### What Happens Behind the Scenes
1. **Alice Profile Generation**: Launches a 3-day trip to Manali for Alice, who prefers slow pacing and cafes.
2. **Bob Profile Generation**: Launches a 3-day trip to Manali for Bob, who prefers fast adventure sports.
3. **Memory Isolation Check**: Audits the persistent database to prove Alice's memory partition is completely isolated from Bob's (and vice-versa).
4. **Style Transfer Test**: Plans a new trip for Alice to Goa, showing her slow pacing and cafe preferences automatically apply to the new destination.

---

## Scenario B: 5-Minute Manual Walkthrough

Use this script during a live interview or demo to show features step-by-step.

### Step 1: Create a Profile with Styles
1. In the sidebar menu, select **🏠 Product Home & Sandbox**.
2. Set User ID to `recruiter_user`.
3. In the input box, type:
   `"Plan a 3 day trip to Jaipur. I want a relaxed pace. I love eating local food in cafes, and please avoid crowded places."`
4. Click **Generate Trip Plan**.
5. *Result*: The multi-agent swarm compiles the itinerary. The sidebar navigation unlocks the other panels.

### Step 2: Inspect Style Extraction
1. Select **🧠 Customer Memory Profile** from the menu.
2. Review the cards. Notice that:
   * **Travel Pace** is set to **Slow** (100% confidence).
   * **Food Style** is set to **Cafes** (100% confidence).
   * **Crowd Preference** is set to **Avoid Crowds** (100% confidence).

### Step 3: Surgical Day Refinement
1. Go to the **✏️ Surgical Refinement** tab.
2. Under "Enter adjustment request", type:
   `"Swap Day 1 afternoon with Day 2 evening"` or `"Remove Albert Hall from Day 1 and add Amber Fort to Day 3"`.
3. Click **Apply Surgical Refinement**.
4. Observe the **Audit Logs**:
   * The log displays the exact days affected.
   * Verify that untouched days remain completely identical.

### Step 4: Examine Decision Trace
1. Select **🔍 Decision Trace & Evidence**.
2. Here, review the grounding information:
   * **Matched Preferences**: Shows how the Planner Agent was guided by the memory trace.
   * **Retrieval Evidence**: Shows the exact RAG documents retrieved from ChromaDB.
   * **Rule Validation Log**: Shows if any duplicate or cross-destination attractions were caught and repaired by the Validator.

### Step 5: Finalize and Test Style Transfer
1. Navigate to the **🏠 Product Home & Sandbox** tab.
2. Scroll down and click **Finalize and Save Plan**. This locks the profile in persistent memory.
3. Change the user query to: `"Plan a 3-day trip to Manali."` (Do not repeat your food or pace preferences).
4. Click **Generate Trip Plan**.
5. Once generated, select the **Interactive Itinerary** and **Customer Memory Profile**.
6. Notice that the new Manali plan is automatically slow-paced, schedules cafe dining, and avoids crowded tourist attractions.
