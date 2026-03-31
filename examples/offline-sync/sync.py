"""Offline mode -- queue actions locally, sync when ready."""
from aira import Aira

aira = Aira(api_key="aira_live_xxx", offline=True)

# Queue actions locally -- no network calls
aira.notarize(action_type="scan_completed", details="Scanned batch #1", agent_id="scanner")
aira.notarize(action_type="scan_completed", details="Scanned batch #2", agent_id="scanner")
aira.notarize(action_type="classification_done", details="Classified 142 docs", agent_id="scanner")

print(f"Queued: {aira._queue.pending_count} actions")

# Sync to API -- cryptographic receipts generated
results = aira.sync()
print(f"Synced: {len(results)} receipts")
for r in results:
    print(f"  Receipt: {r.get('action_id', 'ok')}")
