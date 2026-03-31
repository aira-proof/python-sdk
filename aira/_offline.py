"""Offline queue for Aira SDK — queues actions locally, syncs later."""
import uuid
import threading
from dataclasses import dataclass, field
from typing import Any


@dataclass
class QueuedRequest:
    id: str
    method: str
    path: str
    body: dict


class OfflineQueue:
    """Thread-safe in-memory queue for offline mode."""

    def __init__(self):
        self._items: list[QueuedRequest] = []
        self._lock = threading.Lock()

    def enqueue(self, method: str, path: str, body: dict) -> str:
        qid = f"offline_{uuid.uuid4().hex[:12]}"
        with self._lock:
            self._items.append(QueuedRequest(id=qid, method=method, path=path, body=body))
        return qid

    @property
    def pending_count(self) -> int:
        with self._lock:
            return len(self._items)

    def __len__(self) -> int:
        return self.pending_count

    def clear(self):
        with self._lock:
            self._items.clear()

    def drain(self) -> list[QueuedRequest]:
        """Remove and return all queued items."""
        with self._lock:
            items = list(self._items)
            self._items.clear()
            return items
