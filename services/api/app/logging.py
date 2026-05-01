from __future__ import annotations

import logging
import sys

import structlog


def configure_logging(level: str = "INFO", service: str = "vibebite-api", env: str = "dev") -> None:
    """Configure structlog to emit JSON to stdout.

    Attaches mandatory fields (`service`, `env`) and merges contextvars so
    request-scoped fields (mission_id, user_id, trace_id) propagate.
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True, key="ts"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            _inject_service(service=service, env=env),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def _inject_service(service: str, env: str):
    def processor(_logger, _method, event_dict):
        event_dict.setdefault("service", service)
        event_dict.setdefault("env", env)
        return event_dict

    return processor
