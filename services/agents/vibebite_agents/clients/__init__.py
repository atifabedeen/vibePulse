"""External-service client wrappers.

Each client has a real-shaped public interface and a fixture-driven stub.
The wrapper picks between them based on env vars (see places_client.py and
../models.py). Swapping in a real client at C3 is a one-line change inside
the wrapper.
"""

from __future__ import annotations
