from typing import TypedDict, Annotated, Optional
from langgraph.graph.message import add_messages


class PantryItem(TypedDict):
    name: str
    available: bool


class MedicalProfile(TypedDict):
    conditions: list[str]
    allergies: list[str]
    doctor_notes: list[str]
    last_updated: Optional[str]


class AgentState(TypedDict):
    # Conversation history
    messages: Annotated[list, add_messages]

    # Intake data
    food_request: Optional[str]
    medical_profile: Optional[MedicalProfile]
    pantry: Optional[list[PantryItem]]

    # Nutrition Agent output
    recommendations: Optional[str]
    nutrition_info: Optional[str]
    missing_ingredients: Optional[list[str]]

    # Recipe Agent output
    recipe: Optional[str]
    dish_name: Optional[str]
    youtube_video: Optional[dict]     # {title, link, channel, duration}

    # Order Agent output
    order_status: Optional[str]       # "completed" | "failed" | "nothing_to_order"
    order_result: Optional[str]       # Full order summary
    selected_store: Optional[str]     # Store URL used

    # Flow control
    current_mode: Optional[str]
    next_action: Optional[str]