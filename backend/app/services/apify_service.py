"""
Apify service layer.

Wraps the synchronous Apify Python client in asyncio.to_thread() so it does
not block the FastAPI event loop.

Usage:
    service = ApifyService()
    items = await service.run_actor(actor_id="...", run_input={...})
"""

import asyncio
import logging
from typing import Any

from apify_client import ApifyClient

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class ApifyService:
    """Thin async wrapper around the synchronous Apify Python client."""

    def __init__(self) -> None:
        token = get_settings().apify_api_token
        if not token:
            raise RuntimeError(
                "APIFY_API_TOKEN is not configured. "
                "Add it to your .env file and restart the server."
            )
        # Instantiate the client once per service instance.
        # The token is NOT logged anywhere in this class.
        self._client = ApifyClient(token)

    # ── Public async interface ────────────────────────────────────────────────

    async def run_actor(self, actor_id: str, run_input: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Run an Apify Actor and return its dataset items.

        The underlying Apify client calls are synchronous, so we offload them
        to a thread pool via asyncio.to_thread() to avoid blocking the event loop.

        Args:
            actor_id:  The Apify Actor ID (from APIFY_INSTAGRAM_ACTOR env var).
            run_input: The input dict for the Actor run.

        Returns:
            A list of dicts representing the Actor's dataset items.

        Raises:
            RuntimeError: If the Actor run fails or returns no dataset.
        """
        logger.info("Apify Actor started: %s", actor_id)

        try:
            items = await asyncio.to_thread(
                self._run_actor_sync,
                actor_id,
                run_input,
            )
        except RuntimeError:
            raise
        except Exception as exc:
            logger.exception("Apify Actor error for %s: %s", actor_id, exc)
            raise RuntimeError(
                f"Apify Actor run failed: {type(exc).__name__}. "
                "Check your APIFY_API_TOKEN and Actor configuration."
            ) from exc

        logger.info("Apify Actor finished: %s — %d item(s) returned", actor_id, len(items))
        return items

    # ── Private synchronous implementation ───────────────────────────────────

    def _run_actor_sync(
        self,
        actor_id: str,
        run_input: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Synchronous Apify workflow:
          1. Call actor(actor_id).call(run_input=...) to start a run and wait for it.
          2. Retrieve items from the run's default dataset.

        This method runs inside a thread so it must NOT touch asyncio.
        """
        run = self._client.actor(actor_id).call(run_input=run_input)

        if run is None:
            raise RuntimeError(
                "Apify Actor did not return a run object. "
                "The Actor may have failed to start."
            )

        # Support both Pydantic Run object (run.default_dataset_id) and legacy dict
        dataset_id = getattr(run, "default_dataset_id", None) or getattr(run, "defaultDatasetId", None)
        if not dataset_id and isinstance(run, dict):
            dataset_id = run.get("default_dataset_id") or run.get("defaultDatasetId")

        if not dataset_id:
            raise RuntimeError(
                "Apify Actor run completed but no default_dataset_id was found. "
                "The Actor may have exited without writing data."
            )

        dataset_result = self._client.dataset(dataset_id).list_items()
        if hasattr(dataset_result, "items"):
            items = dataset_result.items
        elif isinstance(dataset_result, dict):
            items = dataset_result.get("items", [])
        elif isinstance(dataset_result, list):
            items = dataset_result
        else:
            items = []

        return items
