"""`score_candidates` LangGraph node.

Deterministic 0-100 scoring of every surviving candidate. No LLM —
this node is the floor of objectivity for the demo: same inputs ->
same scores. The explain step (`explain_candidates`, lands later)
adds free-form prose; this node only computes numbers, pros, and cons.

Reads:
  * `state.candidates`            — what survived `normalize_places`
  * `state.group_constraints`     — emitted by `parse_preferences`
  * `state_ext.CANDIDATE_REGISTRY`— side-channel richer fields

Writes:
  * `state.candidates` with `score`, `pros`, `cons` populated and the
    list sorted by `score` descending (ties broken by rating).

Scoring rubric (sums to 100 before penalties):

  * budget fit   — 25 pts
  * cuisine      — 20 pts (with a -25 penalty for any disliked cuisine
                   match; floors at 0)
  * dietary      — 20 pts
  * noise        — 15 pts
  * vibe         — 10 pts
  * rating       — 10 pts

Pros are derived from components that score at the high end (>=80%
of their weight). Cons are derived from components that score low
(<=25% of their weight). Capped at 3 pros / 2 cons.
"""

from __future__ import annotations

import re
from typing import Any

from ..state import CandidatePlace, GraphState
from ..state_ext import CANDIDATE_REGISTRY, ExtendedCandidate

# ---- Component weights ----------------------------------------------------
W_BUDGET = 25
W_CUISINE = 20
W_DIETARY = 20
W_NOISE = 15
W_VIBE = 10
W_RATING = 10
DISLIKE_PENALTY = 25  # subtracted, score floors at 0


# Rough $ -> cents mapping for budget fit. Mirrors the heuristic in
# implementation.md sec 8.2 score_candidates row.
_PRICE_LEVEL_CENTS = {
    1: 1500,
    2: 3000,
    3: 6000,
    4: 10000,
}

# Cuisines that aren't vegetarian-friendly out of the box.
_VEG_UNFRIENDLY = {"bbq"}
_SUSHI_ONLY_MARKER = {"sushi"}  # only an issue if it's the *sole* cuisine

# Cuisines we treat as vegan-friendly when no explicit flag is present.
_VEGAN_FRIENDLY = {"vegan", "thai", "ethiopian", "indian"}


# ---- helpers --------------------------------------------------------------
def _tokenize_vibe(text: str | None) -> set[str]:
    if not text:
        return set()
    return {t for t in re.split(r"[\s,/-]+", text.lower()) if t}


def _vibe_keywords(ext: ExtendedCandidate) -> set[str]:
    """Pull a set of lowercase vibe tokens off the raw_blob."""
    blob = ext.raw_blob or {}
    raw = blob.get("vibe_keywords")
    if isinstance(raw, list):
        return {str(x).lower() for x in raw}
    # Fallback: tokenize the free-form `vibe` string.
    return _tokenize_vibe(blob.get("vibe"))


def _noise_bucket(noise_tolerance: int | None) -> str:
    """Map the group's tolerance into the same buckets places use."""
    if noise_tolerance is None:
        return "any"
    if noise_tolerance <= 2:
        return "quiet"
    if noise_tolerance == 3:
        return "moderate"
    return "loud"


# ---- component scorers ----------------------------------------------------
def _score_budget(ext: ExtendedCandidate, c: dict[str, Any]) -> tuple[float, str]:
    budget = c.get("budget_max_cents")
    if budget is None:
        # No constraint -> full credit, neutral note.
        return float(W_BUDGET), "no budget constraint"
    cents = _PRICE_LEVEL_CENTS.get(ext.price_level, 10000)
    if cents <= budget:
        return float(W_BUDGET), f"price_level {ext.price_level} fits ${budget/100:.0f} cap"
    return 0.0, f"price_level {ext.price_level} (~${cents/100:.0f}) exceeds ${budget/100:.0f} cap"


def _score_cuisine(ext: ExtendedCandidate, c: dict[str, Any]) -> tuple[float, str]:
    """Returns (score, note). Score may be negative before clamping."""
    cuisines = {x.lower() for x in ext.cuisines}
    likes = {x.lower() for x in (c.get("cuisines_like") or [])}
    dislikes = {x.lower() for x in (c.get("cuisines_dislike") or [])}

    score = 0.0
    notes: list[str] = []

    if cuisines & likes:
        score += 10.0
        notes.append(f"matches liked cuisine ({sorted(cuisines & likes)[0]})")

    if cuisines & dislikes:
        score -= float(DISLIKE_PENALTY)
        notes.append(f"hits disliked cuisine ({sorted(cuisines & dislikes)[0]})")

    return score, "; ".join(notes) if notes else "no cuisine signal"


def _score_dietary(ext: ExtendedCandidate, c: dict[str, Any]) -> tuple[float, str]:
    dietary = {d.lower() for d in (c.get("dietary_restrictions") or [])}
    if not dietary:
        return float(W_DIETARY), "no dietary restrictions"

    cuisines = {x.lower() for x in ext.cuisines}
    blob = ext.raw_blob or {}

    # Vegetarian: penalize cuisines with no veg signal AND blob doesn't say
    # otherwise. The fixtures generally tag `vegetarian_options` directly.
    if "vegetarian" in dietary:
        veg_flag = blob.get("vegetarian_options")
        if veg_flag is False:
            return 0.0, "raw_blob: no vegetarian options"
        if veg_flag is None and (cuisines & _VEG_UNFRIENDLY):
            return 0.0, "cuisine unfriendly to vegetarians"
        # sushi-only places technically have veg rolls, but they're sparse —
        # only penalize if sushi is the *sole* listed cuisine.
        if veg_flag is None and cuisines == _SUSHI_ONLY_MARKER:
            return 0.0, "sushi-only restaurant"

    if "vegan" in dietary:
        if blob.get("vegan_options") is True:
            return float(W_DIETARY), "raw_blob: vegan options"
        if cuisines & _VEGAN_FRIENDLY:
            return float(W_DIETARY), "cuisine vegan-friendly"
        return 0.0, "no vegan signal"

    return float(W_DIETARY), "dietary needs satisfiable"


def _score_noise(ext: ExtendedCandidate, c: dict[str, Any]) -> tuple[float, str]:
    bucket = _noise_bucket(c.get("noise_tolerance"))
    place_noise = (ext.raw_blob or {}).get("noise")
    if bucket == "any" or place_noise is None:
        return float(W_NOISE), "no noise constraint"
    if str(place_noise).lower() == bucket:
        return float(W_NOISE), f"noise '{place_noise}' matches '{bucket}' bucket"
    # Half credit when the place's noise is one bucket off feels too generous —
    # the spec calls for 7 on mismatch.
    return 7.0, f"noise '{place_noise}' vs preferred '{bucket}'"


def _score_vibe(ext: ExtendedCandidate, c: dict[str, Any]) -> tuple[float, str]:
    group_vibe = c.get("vibe")
    if not group_vibe:
        return float(W_VIBE), "no group vibe"
    group_tokens = _tokenize_vibe(group_vibe)
    cand_tokens = _vibe_keywords(ext)
    overlap = group_tokens & cand_tokens
    if overlap:
        return float(W_VIBE), f"vibe overlap: {sorted(overlap)}"
    return 0.0, f"no vibe overlap (wanted {sorted(group_tokens)})"


def _score_rating(ext: ExtendedCandidate) -> tuple[float, str]:
    raw = (ext.rating - 3.0) / 1.8 * 10.0
    score = max(0.0, min(float(W_RATING), raw))
    return score, f"rating {ext.rating}"


# ---- pros/cons synthesis --------------------------------------------------
def _label_for(component: str, ext: ExtendedCandidate, c: dict[str, Any]) -> str:
    """Friendly one-liner for a high-scoring component."""
    if component == "budget":
        return "Fits the group's budget."
    if component == "cuisine":
        likes = {x.lower() for x in (c.get("cuisines_like") or [])}
        match = sorted({x.lower() for x in ext.cuisines} & likes)
        return f"Cuisine match ({match[0]})." if match else "Cuisine works for the group."
    if component == "dietary":
        return "Dietary needs are covered."
    if component == "noise":
        return "Noise level matches what the group asked for."
    if component == "vibe":
        return "Vibe lines up with the group's mood."
    if component == "rating":
        return f"Strong rating ({ext.rating})."
    return component


def _con_for(component: str, ext: ExtendedCandidate, c: dict[str, Any]) -> str:
    if component == "budget":
        return "Pricier than the group's budget cap."
    if component == "cuisine":
        dislikes = {x.lower() for x in (c.get("cuisines_dislike") or [])}
        hit = sorted({x.lower() for x in ext.cuisines} & dislikes)
        if hit:
            return f"Cuisine includes a disliked option ({hit[0]})."
        return "Cuisine doesn't lean into what the group likes."
    if component == "dietary":
        return "Dietary restrictions may be hard to satisfy here."
    if component == "noise":
        return "Noise level is off from what the group wants."
    if component == "vibe":
        return "Vibe doesn't quite match the group's mood."
    if component == "rating":
        return f"Rating is on the lower side ({ext.rating})."
    return component


def _build_pros_cons(
    ext: ExtendedCandidate,
    c: dict[str, Any],
    components: dict[str, tuple[float, float]],  # name -> (raw, weight)
) -> tuple[list[str], list[str]]:
    pros: list[str] = []
    cons: list[str] = []

    # Sort components by ratio descending for pros, ascending for cons.
    ratios = []
    for name, (raw, weight) in components.items():
        if weight <= 0:
            continue
        ratios.append((name, raw / weight, raw, weight))

    ratios_high = sorted(ratios, key=lambda r: (-r[1], r[0]))
    for name, ratio, _raw, _w in ratios_high:
        if ratio >= 0.8 and len(pros) < 3:
            pros.append(_label_for(name, ext, c))

    ratios_low = sorted(ratios, key=lambda r: (r[1], r[0]))
    for name, ratio, _raw, _w in ratios_low:
        if ratio <= 0.25 and len(cons) < 2:
            cons.append(_con_for(name, ext, c))

    return pros, cons


# ---- node -----------------------------------------------------------------
async def score_candidates(state: GraphState) -> dict[str, Any]:
    """Compute a deterministic 0-100 score for each surviving candidate."""
    constraints = state.group_constraints or {}
    scored: list[tuple[float, float, CandidatePlace]] = []

    for cand in state.candidates:
        ext = CANDIDATE_REGISTRY.get(str(cand.place_id))
        if ext is None:
            # Defensive: normalize_places should have dropped these. If a
            # candidate sneaks in without the registry record, score it 0.
            cand_copy = cand.model_copy(update={"score": 0.0, "pros": [], "cons": ["Missing place data."]})
            scored.append((0.0, 0.0, cand_copy))
            continue

        budget_s, _ = _score_budget(ext, constraints)
        cuisine_s, _ = _score_cuisine(ext, constraints)
        dietary_s, _ = _score_dietary(ext, constraints)
        noise_s, _ = _score_noise(ext, constraints)
        vibe_s, _ = _score_vibe(ext, constraints)
        rating_s, _ = _score_rating(ext)

        total = budget_s + cuisine_s + dietary_s + noise_s + vibe_s + rating_s
        total = max(0.0, min(100.0, total))

        # Cuisine raw can be negative; clamp for the pros/cons ratio math.
        cuisine_for_ratio = max(0.0, cuisine_s)

        components = {
            "budget": (budget_s, float(W_BUDGET)),
            "cuisine": (cuisine_for_ratio, float(W_CUISINE)),
            "dietary": (dietary_s, float(W_DIETARY)),
            "noise": (noise_s, float(W_NOISE)),
            "vibe": (vibe_s, float(W_VIBE)),
            "rating": (rating_s, float(W_RATING)),
        }
        pros, cons = _build_pros_cons(ext, constraints, components)

        # Special-case: a disliked-cuisine hit always shows up as a con.
        if cuisine_s < 0:
            tag = _con_for("cuisine", ext, constraints)
            if tag not in cons:
                if len(cons) >= 2:
                    cons[-1] = tag
                else:
                    cons.append(tag)

        cand_copy = cand.model_copy(update={
            "score": round(total, 2),
            "pros": pros,
            "cons": cons,
        })
        # Sort key: score desc, then rating desc, then name asc.
        scored.append((total, ext.rating, cand_copy))

    scored.sort(key=lambda row: (-row[0], -row[1], row[2].name))
    sorted_candidates = [row[2] for row in scored]

    return {"candidates": sorted_candidates}


__all__ = ["score_candidates"]


if __name__ == "__main__":
    import asyncio

    from ..fixtures.sample_mission import sample_mission_state
    from ..state_ext import reset_registry
    from .normalize_places import normalize_places
    from .search_places import search_places

    async def _smoke() -> None:
        reset_registry()
        state = sample_mission_state()
        # Hardcoded sample group_constraints (vegetarian + quiet + budget).
        # C2-A's parse_preferences will eventually emit this for real;
        # we don't depend on its completion.
        state.group_constraints = {
            "budget_max_cents": 2000,
            "cuisines_like": ["italian", "thai", "indian"],
            "cuisines_dislike": ["sushi"],
            "dietary_restrictions": ["vegetarian"],
            "vibe": "casual",
            "noise_tolerance": 2,
            "summary": "smoke-test constraints: vegetarian + quiet + budget",
        }

        # Run the chain in order so the registry is populated.
        s_update = await search_places(state)
        state.candidates = s_update["candidates"]
        n_update = await normalize_places(state)
        state.candidates = n_update["candidates"]
        sc_update = await score_candidates(state)

        print(f"\nscore_candidates: top 5 of {len(sc_update['candidates'])} ranked\n")
        for cand in sc_update["candidates"][:5]:
            print(f"  {cand.score:6.2f}  {cand.name}")
            for p in cand.pros:
                print(f"          + {p}")
            for c in cand.cons:
                print(f"          - {c}")

    asyncio.run(_smoke())
