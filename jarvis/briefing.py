from __future__ import annotations

from .models import HouseholdProfile, UserProfile


def build_morning_brief(household: HouseholdProfile, actor: UserProfile) -> str:
    if actor.user_id == "chris":
        return (
            f"Good morning, {actor.address_as}. "
            "Body: hydration and light mobility. "
            "Home: check rain timing, freezer variance, and departure loops. "
            "Mission: strategy block, manuscript editing, and workshop prototype."
        )
    if actor.user_id == "rebekah":
        return (
            f"Good morning, {actor.address_as}. "
            "Family: groceries, troop timing, and parent communication. "
            "Home: departure choreography and evening meal planning. "
            "Mission: keep the day calm and visible."
        )
    return (
        f"Good morning, {actor.address_as}. "
        f"You are in the {household.household_name}. "
        "Focus on the next faithful step."
    )
