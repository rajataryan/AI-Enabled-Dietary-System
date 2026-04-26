from langgraph.graph import StateGraph, END
from state import AgentState
from intake_agent import (
    food_request_node,
    medical_update_node,
    pantry_update_node,
    intake_router
)
from nutrition_agent import nutrition_agent_node
from recipe_agent import recipe_agent_node
from order_agent import order_agent_node


# ─────────────────────────────────────────────
# Routers
# ─────────────────────────────────────────────

def post_intake_router(state: AgentState) -> str:
    next_action = state.get("next_action", "end")
    if next_action == "nutrition_agent":
        return "nutrition_agent_node"
    return "end"


def post_nutrition_router(state: AgentState) -> str:
    next_action = state.get("next_action", "end")
    if next_action == "recipe_agent":
        return "recipe_agent_node"
    return "end"


def post_recipe_router(state: AgentState) -> str:
    next_action = state.get("next_action", "end")
    if next_action == "order_agent":
        return "order_agent_node"
    return "end"


# ─────────────────────────────────────────────
# Build Graph
# ─────────────────────────────────────────────

def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    # ── Add Nodes ──
    graph.add_node("food_request_node", food_request_node)
    graph.add_node("medical_update_node", medical_update_node)
    graph.add_node("pantry_update_node", pantry_update_node)
    graph.add_node("nutrition_agent_node", nutrition_agent_node)
    graph.add_node("recipe_agent_node", recipe_agent_node)
    graph.add_node("order_agent_node", order_agent_node)

    # ── Entry Point ──
    graph.set_conditional_entry_point(
        intake_router,
        {
            "food_request_node": "food_request_node",
            "medical_update_node": "medical_update_node",
            "pantry_update_node": "pantry_update_node",
            "end": END
        }
    )

    # ── Edges ──
    # Intake → Nutrition
    graph.add_conditional_edges(
        "food_request_node",
        post_intake_router,
        {
            "nutrition_agent_node": "nutrition_agent_node",
            "end": END
        }
    )

    # Nutrition → Recipe
    graph.add_conditional_edges(
        "nutrition_agent_node",
        post_nutrition_router,
        {
            "recipe_agent_node": "recipe_agent_node",
            "end": END
        }
    )

    # Recipe → Order
    graph.add_conditional_edges(
        "recipe_agent_node",
        post_recipe_router,
        {
            "order_agent_node": "order_agent_node",
            "end": END
        }
    )

    # Order → END
    graph.add_edge("order_agent_node", END)
    graph.add_edge("medical_update_node", END)
    graph.add_edge("pantry_update_node", END)

    return graph.compile()