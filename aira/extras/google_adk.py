"""Google ADK integration — notarize tool calls via plugin hooks."""
from __future__ import annotations
import logging
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from aira import Aira

logger = logging.getLogger(__name__)


class AiraPlugin:
    """Google ADK plugin that notarizes tool calls via Aira."""

    def __init__(self, client: "Aira", agent_id: str, model_id: str | None = None):
        self.client = client
        self.agent_id = agent_id
        self.model_id = model_id

    def _notarize(self, action_type: str, details: str) -> None:
        try:
            kwargs: dict[str, Any] = {"action_type": action_type, "details": details[:5000], "agent_id": self.agent_id}
            if self.model_id:
                kwargs["model_id"] = self.model_id
            self.client.notarize(**kwargs)
        except Exception as e:
            logger.warning("Aira notarize failed (non-blocking): %s", e)

    def before_tool_call(self, tool_name: str, args: dict | None = None) -> None:
        """ADK before_tool_call hook."""
        arg_keys = list((args or {}).keys())
        self._notarize("tool_invoked", f"Tool '{tool_name}' invoked. Arg keys: {arg_keys}")

    def after_tool_call(self, tool_name: str, result: Any = None) -> None:
        """ADK after_tool_call hook."""
        self._notarize("tool_completed", f"Tool '{tool_name}' completed. Result length: {len(str(result))} chars")
