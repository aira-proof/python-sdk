"""CrewAI integration — notarize task and step completions."""
from __future__ import annotations
import logging
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from aira import Aira

logger = logging.getLogger(__name__)


class AiraCrewHook:
    """CrewAI hook that notarizes task completions via Aira."""

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

    def task_callback(self, output: Any) -> None:
        """Called by CrewAI when a task completes."""
        desc = str(getattr(output, "description", ""))[:200]
        self._notarize("task_completed", f"Task completed: {desc}")

    def step_callback(self, step_output: Any) -> None:
        """Called by CrewAI on each agent step."""
        self._notarize("agent_step", f"Agent step completed. Output length: {len(str(step_output))} chars")

    @classmethod
    def for_crew(cls, client: "Aira", agent_id: str, **kwargs) -> dict[str, Any]:
        """Return callbacks dict compatible with CrewAI's Crew() constructor."""
        hook = cls(client, agent_id, **kwargs)
        return {
            "task_callback": hook.task_callback,
            "step_callback": hook.step_callback,
        }
