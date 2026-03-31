# Aira Offline Sync

Queue notarization actions locally when offline, then batch-sync when connectivity is available.

## Setup

```bash
pip install aira-sdk
```

## Run

```bash
export AIRA_API_KEY="aira_live_xxx"
python sync.py
```

## How It Works

1. Initialize `Aira(offline=True)` to enable local queuing
2. Call `aira.notarize(...)` as usual -- actions are stored locally, no network calls
3. Call `aira.sync()` when ready to push all queued actions to the API
4. Each synced action receives a cryptographic receipt

## Use Cases

- Edge devices with intermittent connectivity
- Batch processing where you want to notarize many actions at once
- Environments where network calls during processing add unacceptable latency
