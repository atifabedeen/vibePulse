"""Google Places client wrapper.

Real-shaped public surface so downstream nodes call the same method
regardless of whether they are hitting Google or the local stub.

Selection rules:

  * If `VIBEBITE_USE_STUBS=1` is set, the stub is always used.
  * Else if `GOOGLE_PLACES_API_KEY` is unset, the stub is used.
  * Otherwise the real client is used (NotImplemented at C1-C; lands in C3).

Swapping in the real implementation later is a single-block change inside
`text_search`.
"""

from __future__ import annotations

import os
from typing import Optional

from .places_stub import PlaceResult, stub_text_search


class GooglePlacesClient:
    """Thin wrapper around Google Places Text Search.

    Public methods mirror the real client we will introduce in C3. The C1-C
    implementation defers to the fixture stub when no API key is present
    (or when stubs are explicitly forced).
    """

    def __init__(self, api_key: Optional[str] = None, force_stub: Optional[bool] = None) -> None:
        self._api_key = api_key if api_key is not None else os.environ.get("GOOGLE_PLACES_API_KEY")
        if force_stub is None:
            force_stub = os.environ.get("VIBEBITE_USE_STUBS") == "1"
        self._use_stub = force_stub or not self._api_key

    @property
    def using_stub(self) -> bool:
        """True when this instance will return fixture data."""
        return self._use_stub

    def text_search(
        self,
        query: str,
        lat: float,
        lng: float,
        radius_m: int,
        max_results: int = 12,
    ) -> list[PlaceResult]:
        """Run a Places Text Search biased to (lat, lng, radius_m).

        Returns up to `max_results` `PlaceResult` records. On stub mode this
        is the canned Atlanta fixture set.
        """
        if self._use_stub:
            return stub_text_search(query, lat, lng, radius_m, max_results=max_results)

        # Real client lands in C3. Keeping this branch unreachable-but-explicit
        # so the file communicates intent without pulling in httpx wiring yet.
        raise NotImplementedError(
            "Real Google Places client lands in C3. Set VIBEBITE_USE_STUBS=1 "
            "or unset GOOGLE_PLACES_API_KEY to use the fixture stub."
        )


__all__ = ["GooglePlacesClient", "PlaceResult"]
