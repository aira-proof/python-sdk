# LangChain Agent with Aira Notarization

Every tool call and chain completion gets a cryptographic receipt via `AiraCallbackHandler`.

## Setup

```bash
pip install aira-sdk[langchain] langchain-openai
```

## Environment Variables

```bash
export AIRA_API_KEY="aira_live_xxx"
export OPENAI_API_KEY="sk-xxx"
```

## Run

```bash
python agent.py
```

## How It Works

1. `AiraCallbackHandler` hooks into LangChain's callback system
2. Every `on_tool_end` call notarizes the tool invocation with Aira
3. `on_chain_end` notarizes the final chain output
4. Each notarization returns a cryptographic receipt for audit

## Integration

Pass the handler via LangChain's `config={"callbacks": [handler]}` on any chain or agent invocation.
