"""Prompt templates for the recommendation graph.

Implementation.md section 9.3 enumerates three prompts. The actual prompt
engineering happens in C2 alongside the real LangGraph nodes; for C1-C we
just commit placeholder constants so node code can `from .prompts import
GROUP_FOOD_RECOMMENDATION` without exploding.

These strings are intentionally short. They are NOT production prompts —
real templates will be templated with member preferences, location, and
candidate context, and will instruct the model to emit JSON conforming to
the Pydantic response models.
"""

from __future__ import annotations

# Used by parse_preferences and explain_candidates.
# Variables (filled in by node code at C2): member_prefs, location.
GROUP_FOOD_RECOMMENDATION = """\
You are VibeBite, an assistant that helps a group of friends agree on a
restaurant. Given the members' raw preferences and the search location,
extract a single shared constraint profile (budget, dietary restrictions,
vibe, noise tolerance, cuisines liked/disliked) that respects every
member's hard constraints.

Members:
{member_prefs}

Location:
{location}

Return JSON conforming to the GroupConstraints schema.
"""

# Used by explain_candidates, once per candidate.
# Variables: place, group_constraints.
RESTAURANT_TRADEOFF_EXPLANATION = """\
You are explaining why a single restaurant is or is not a good fit for a
group. Be concise and concrete. Cite specific facts from the place blob.

Place:
{place}

Group constraints:
{group_constraints}

Return JSON with `pros` and `cons` arrays of short strings.
"""

# Used by reliability_check to summarize signals into an incident row.
# Variables: signals, recent_runs.
INCIDENT_SUMMARY = """\
You are VibeBite's reliability summarizer. Given recent agent run signals
and any external API errors, produce a one-paragraph incident description
suitable for the `incidents.details` JSON field.

Signals:
{signals}

Recent runs:
{recent_runs}

Return JSON with `title`, `severity`, and `summary` fields.
"""
