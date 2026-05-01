"""Fixture-driven Google Places stub.

Returns 12 hand-crafted realistic restaurants near Atlanta GA
(33.749, -84.388). Coverage is intentional:

  * cuisines: italian, mexican, japanese, thai, vegan, american,
    indian, korean, ethiopian, pizza, burgers, ramen
  * price_level: full spread across 1-4
  * rating: 3.5 - 4.8
  * vibe: at least 2 vegetarian-friendly, 2 quiet/casual, 2 lively
  * each entry has a stable UUID-shaped `id` and a `google_place_id`

The stub returns `list[PlaceResult]` so call sites can treat it
identically to the real client. raw_blob mimics the shape that the real
Places Text Search response would deliver (subset that we actually use).
"""

from __future__ import annotations

import math
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class PlaceResult(BaseModel):
    """One restaurant, in the shape downstream nodes expect.

    Mirrors the columns we will eventually upsert into the `places` table.
    `raw_blob` is the verbatim Places payload (subset, here) so the score
    and explain nodes can read free-form vibe/review text.
    """

    id: str                       # internal stable UUID-shaped id
    google_place_id: str
    name: str
    address: str
    lat: float
    lng: float
    price_level: int = Field(ge=0, le=4)
    rating: float
    user_rating_ct: int
    cuisines: list[str] = Field(default_factory=list)
    raw_blob: dict[str, Any] = Field(default_factory=dict)


# Atlanta downtown anchor.
_ATL_LAT = 33.749
_ATL_LNG = -84.388


def _offset(lat: float, lng: float, dlat_km: float, dlng_km: float) -> tuple[float, float]:
    """Approximate offset in km. Good enough for fixtures."""
    new_lat = lat + (dlat_km / 110.574)
    new_lng = lng + (dlng_km / (111.320 * math.cos(math.radians(lat))))
    return round(new_lat, 6), round(new_lng, 6)


# 12 fixture restaurants. Coordinates spread within ~3km of the Atlanta anchor.
_FIXTURES: list[PlaceResult] = [
    PlaceResult(
        id="11111111-1111-4111-8111-111111111101",
        google_place_id="ChIJstub_italian_001",
        name="Trattoria Lucia",
        address="225 Peachtree St NE, Atlanta, GA 30303",
        lat=_offset(_ATL_LAT, _ATL_LNG, 0.4, 0.2)[0],
        lng=_offset(_ATL_LAT, _ATL_LNG, 0.4, 0.2)[1],
        price_level=3,
        rating=4.5,
        user_rating_ct=842,
        cuisines=["italian"],
        raw_blob={
            "vibe": "warm dimly-lit trattoria, candles on tables, romantic but unfussy",
            "noise": "quiet",
            "good_for_groups": True,
            "vegetarian_options": True,
            "summary": "Family-run northern Italian, hand-rolled pasta, intimate seating.",
        },
    ),
    PlaceResult(
        id="11111111-1111-4111-8111-111111111102",
        google_place_id="ChIJstub_mexican_002",
        name="El Patio Cantina",
        address="510 N Highland Ave, Atlanta, GA 30307",
        lat=_offset(_ATL_LAT, _ATL_LNG, 1.1, -0.6)[0],
        lng=_offset(_ATL_LAT, _ATL_LNG, 1.1, -0.6)[1],
        price_level=2,
        rating=4.2,
        user_rating_ct=1503,
        cuisines=["mexican"],
        raw_blob={
            "vibe": "lively colorful patio, mariachi on weekends, picnic tables, festive",
            "noise": "loud",
            "good_for_groups": True,
            "vegetarian_options": True,
            "summary": "Tex-mex classics, great margaritas, big patio, group-friendly.",
        },
    ),
    PlaceResult(
        id="11111111-1111-4111-8111-111111111103",
        google_place_id="ChIJstub_japanese_003",
        name="Umi Sushi",
        address="3050 Peachtree Rd NW, Atlanta, GA 30305",
        lat=_offset(_ATL_LAT, _ATL_LNG, 2.4, 0.9)[0],
        lng=_offset(_ATL_LAT, _ATL_LNG, 2.4, 0.9)[1],
        price_level=4,
        rating=4.7,
        user_rating_ct=617,
        cuisines=["japanese", "sushi"],
        raw_blob={
            "vibe": "sleek minimalist sushi counter, hushed, special-occasion",
            "noise": "quiet",
            "good_for_groups": False,
            "vegetarian_options": True,
            "summary": "Omakase-driven sushi bar, premium fish, refined service.",
        },
    ),
    PlaceResult(
        id="11111111-1111-4111-8111-111111111104",
        google_place_id="ChIJstub_thai_004",
        name="Bangkok Street Kitchen",
        address="1232 Ponce de Leon Ave NE, Atlanta, GA 30306",
        lat=_offset(_ATL_LAT, _ATL_LNG, 1.5, 0.3)[0],
        lng=_offset(_ATL_LAT, _ATL_LNG, 1.5, 0.3)[1],
        price_level=2,
        rating=4.3,
        user_rating_ct=982,
        cuisines=["thai"],
        raw_blob={
            "vibe": "casual neighborhood thai spot, quick service, mid-volume",
            "noise": "moderate",
            "good_for_groups": True,
            "vegetarian_options": True,
            "summary": "Honest pad thai, generous portions, plenty of veg curries.",
        },
    ),
    PlaceResult(
        id="11111111-1111-4111-8111-111111111105",
        google_place_id="ChIJstub_vegan_005",
        name="Plant Haus",
        address="675 Ponce de Leon Ave NE, Atlanta, GA 30308",
        lat=_offset(_ATL_LAT, _ATL_LNG, 1.0, 0.1)[0],
        lng=_offset(_ATL_LAT, _ATL_LNG, 1.0, 0.1)[1],
        price_level=2,
        rating=4.6,
        user_rating_ct=731,
        cuisines=["vegan", "american"],
        raw_blob={
            "vibe": "bright airy plant-filled cafe, casual, instagrammable",
            "noise": "moderate",
            "good_for_groups": True,
            "vegetarian_options": True,
            "vegan_options": True,
            "summary": "Fully vegan menu, jackfruit tacos, oat-milk lattes, brunch crowd.",
        },
    ),
    PlaceResult(
        id="11111111-1111-4111-8111-111111111106",
        google_place_id="ChIJstub_american_006",
        name="The Smokestack",
        address="450 Memorial Dr SE, Atlanta, GA 30312",
        lat=_offset(_ATL_LAT, _ATL_LNG, -0.9, 0.7)[0],
        lng=_offset(_ATL_LAT, _ATL_LNG, -0.9, 0.7)[1],
        price_level=3,
        rating=4.4,
        user_rating_ct=2104,
        cuisines=["american", "bbq"],
        raw_blob={
            "vibe": "rowdy bbq joint, beer hall energy, picnic tables, music loud",
            "noise": "loud",
            "good_for_groups": True,
            "vegetarian_options": False,
            "summary": "Smoked brisket, ribs, burnt ends, packed on weekends.",
        },
    ),
    PlaceResult(
        id="11111111-1111-4111-8111-111111111107",
        google_place_id="ChIJstub_indian_007",
        name="Saffron House",
        address="2089 Cheshire Bridge Rd NE, Atlanta, GA 30324",
        lat=_offset(_ATL_LAT, _ATL_LNG, 2.7, 1.1)[0],
        lng=_offset(_ATL_LAT, _ATL_LNG, 2.7, 1.1)[1],
        price_level=2,
        rating=4.4,
        user_rating_ct=1188,
        cuisines=["indian"],
        raw_blob={
            "vibe": "warm spice-scented dining room, white tablecloths, soft music",
            "noise": "quiet",
            "good_for_groups": True,
            "vegetarian_options": True,
            "summary": "North & South Indian, half the menu is vegetarian, dosa bar.",
        },
    ),
    PlaceResult(
        id="11111111-1111-4111-8111-111111111108",
        google_place_id="ChIJstub_korean_008",
        name="Seoul BBQ House",
        address="5150 Buford Hwy NE, Atlanta, GA 30340",
        lat=_offset(_ATL_LAT, _ATL_LNG, 2.9, -1.0)[0],
        lng=_offset(_ATL_LAT, _ATL_LNG, 2.9, -1.0)[1],
        price_level=3,
        rating=4.5,
        user_rating_ct=1652,
        cuisines=["korean", "bbq"],
        raw_blob={
            "vibe": "smoky tabletop grill, energetic, groups clinking soju glasses",
            "noise": "loud",
            "good_for_groups": True,
            "vegetarian_options": False,
            "summary": "All-you-can-eat KBBQ, banchan, late-night crowd.",
        },
    ),
    PlaceResult(
        id="11111111-1111-4111-8111-111111111109",
        google_place_id="ChIJstub_ethiopian_009",
        name="Queen of Sheba",
        address="1594 Woodland Ave SE, Atlanta, GA 30316",
        lat=_offset(_ATL_LAT, _ATL_LNG, -1.2, 0.4)[0],
        lng=_offset(_ATL_LAT, _ATL_LNG, -1.2, 0.4)[1],
        price_level=1,
        rating=4.6,
        user_rating_ct=523,
        cuisines=["ethiopian"],
        raw_blob={
            "vibe": "cozy intimate room, low lighting, communal injera platters",
            "noise": "quiet",
            "good_for_groups": True,
            "vegetarian_options": True,
            "summary": "Family-run Ethiopian, the veggie combo is the move, cheap.",
        },
    ),
    PlaceResult(
        id="11111111-1111-4111-8111-111111111110",
        google_place_id="ChIJstub_pizza_010",
        name="Antico Pizza Napoletana",
        address="1093 Hemphill Ave NW, Atlanta, GA 30318",
        lat=_offset(_ATL_LAT, _ATL_LNG, 2.0, -1.4)[0],
        lng=_offset(_ATL_LAT, _ATL_LNG, 2.0, -1.4)[1],
        price_level=2,
        rating=4.5,
        user_rating_ct=3201,
        cuisines=["pizza", "italian"],
        raw_blob={
            "vibe": "open kitchen, communal tables, wood-fired chaos, lively",
            "noise": "loud",
            "good_for_groups": True,
            "vegetarian_options": True,
            "summary": "Neapolitan pies straight from the oven, cash-friendly, no reservations.",
        },
    ),
    PlaceResult(
        id="11111111-1111-4111-8111-111111111111",
        google_place_id="ChIJstub_burgers_011",
        name="Grindhouse Killer Burgers",
        address="701 Memorial Dr SE, Atlanta, GA 30312",
        lat=_offset(_ATL_LAT, _ATL_LNG, -0.7, 0.8)[0],
        lng=_offset(_ATL_LAT, _ATL_LNG, -0.7, 0.8)[1],
        price_level=1,
        rating=3.5,
        user_rating_ct=874,
        cuisines=["burgers", "american"],
        raw_blob={
            "vibe": "diner-counter casual, neon, fast in-and-out",
            "noise": "moderate",
            "good_for_groups": False,
            "vegetarian_options": True,
            "summary": "Cheap smashburgers, has a black bean option, milkshakes.",
        },
    ),
    PlaceResult(
        id="11111111-1111-4111-8111-111111111112",
        google_place_id="ChIJstub_ramen_012",
        name="Hakata Ramen Bar",
        address="384 Northside Dr NW, Atlanta, GA 30318",
        lat=_offset(_ATL_LAT, _ATL_LNG, 0.7, -1.2)[0],
        lng=_offset(_ATL_LAT, _ATL_LNG, 0.7, -1.2)[1],
        price_level=2,
        rating=4.3,
        user_rating_ct=689,
        cuisines=["ramen", "japanese"],
        raw_blob={
            "vibe": "small steamy ramen counter, tucked away, quiet weekday nights",
            "noise": "quiet",
            "good_for_groups": False,
            "vegetarian_options": True,
            "summary": "Tonkotsu broth simmered 18 hours; veg shoyu also on the menu.",
        },
    ),
]


def stub_text_search(
    query: str,
    lat: float,
    lng: float,
    radius_m: int,
    max_results: int = 12,
) -> list[PlaceResult]:
    """Return the fixture restaurants, ignoring the query (this is a stub).

    The real client (added in C3) will call Google Places Text Search; this
    stub returns realistic data so downstream nodes (score, explain) have
    something to work with during development.
    """
    # Args are unused on purpose — keep them in the signature so swapping in
    # the real client is mechanical.
    del query, lat, lng, radius_m
    return list(_FIXTURES[:max_results])


__all__ = ["PlaceResult", "stub_text_search"]
