"""A canonical 5-member fixture mission for the demo runner.

`sample_mission_state()` returns a populated `GraphState` representing a
group of five friends planning dinner in Atlanta with mixed vibes,
budgets, and dietary needs. C2's demo will pipe this into the LangGraph
graph; until then it is callable directly so unit tests can exercise the
stubs end-to-end.
"""

from __future__ import annotations

from uuid import UUID

from ..state import GraphState, MemberPref

# Stable UUIDs so logs/snapshots stay deterministic.
_MISSION_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaa01")
_AGENT_RUN_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaa02")

_USER_IDS = [
    UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbb01"),
    UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbb02"),
    UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbb03"),
    UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbb04"),
    UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbb05"),
]


def sample_mission_state() -> GraphState:
    """Return a fixture `GraphState` ready for the recommend graph."""
    member_prefs = [
        MemberPref(
            user_id=_USER_IDS[0],
            structured={
                "budget_max_cents": 2500,
                "distance_tolerance_m": 3000,
                "cuisines_like": ["italian", "thai"],
                "cuisines_dislike": [],
                "dietary_restrictions": ["vegetarian"],
                "vibe": "casual",
                "noise_tolerance": 2,
                "seating_preference": "either",
                "urgency": 2,
                "hunger_level": 4,
            },
            raw_comment="I'm vegetarian and want something casual but cute, not too loud.",
        ),
        MemberPref(
            user_id=_USER_IDS[1],
            structured={
                "budget_max_cents": 2000,
                "distance_tolerance_m": 4000,
                "cuisines_like": ["mexican", "korean"],
                "cuisines_dislike": ["sushi"],
                "dietary_restrictions": [],
                "vibe": "lively",
                "noise_tolerance": 5,
                "seating_preference": "indoor",
                "urgency": 3,
                "hunger_level": 5,
            },
            raw_comment="Hard no on sushi. Want somewhere lively with good drinks.",
        ),
        MemberPref(
            user_id=_USER_IDS[2],
            structured={
                "budget_max_cents": 1500,
                "distance_tolerance_m": 2500,
                "cuisines_like": ["pizza", "burgers"],
                "cuisines_dislike": [],
                "dietary_restrictions": [],
                "vibe": "casual",
                "noise_tolerance": 4,
                "seating_preference": "either",
                "urgency": 4,
                "hunger_level": 5,
            },
            raw_comment="Cheap and fast please, I'm starving.",
        ),
        MemberPref(
            user_id=_USER_IDS[3],
            structured={
                "budget_max_cents": 5000,
                "distance_tolerance_m": 5000,
                "cuisines_like": ["japanese"],
                "cuisines_dislike": [],
                "dietary_restrictions": [],
                "vibe": "quiet",
                "noise_tolerance": 1,
                "seating_preference": "indoor",
                "urgency": 1,
                "hunger_level": 2,
            },
            raw_comment="Somewhere quiet would be ideal — I want to actually hear people.",
        ),
        MemberPref(
            user_id=_USER_IDS[4],
            structured={
                "budget_max_cents": 3000,
                "distance_tolerance_m": 3500,
                "cuisines_like": ["indian", "ethiopian"],
                "cuisines_dislike": [],
                "dietary_restrictions": ["vegan"],
                "vibe": "casual",
                "noise_tolerance": 3,
                "seating_preference": "either",
                "urgency": 2,
                "hunger_level": 3,
            },
            raw_comment="Vegan, mid-budget, casual vibe is fine.",
        ),
    ]

    return GraphState(
        mission_id=_MISSION_ID,
        member_prefs=member_prefs,
        location=(33.749, -84.388),  # Atlanta GA
        search_radius_m=3000,
        agent_run_id=_AGENT_RUN_ID,
    )


__all__ = ["sample_mission_state"]
