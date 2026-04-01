"""Tests for the LangChain callback handler integration."""
from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import MagicMock, patch


# Mock langchain_core at module level so tests run without installing it
_mock_langchain_core = types.ModuleType("langchain_core")
_mock_callbacks = types.ModuleType("langchain_core.callbacks")
_mock_callbacks_base = types.ModuleType("langchain_core.callbacks.base")


class _MockBaseCallbackHandler:
    """Minimal stand-in for langchain_core BaseCallbackHandler."""
    pass


_mock_callbacks_base.BaseCallbackHandler = _MockBaseCallbackHandler
_mock_callbacks.base = _mock_callbacks_base
_mock_langchain_core.callbacks = _mock_callbacks

sys.modules["langchain_core"] = _mock_langchain_core
sys.modules["langchain_core.callbacks"] = _mock_callbacks
sys.modules["langchain_core.callbacks.base"] = _mock_callbacks_base

# Now we can import the module under test
from aira.extras.langchain import AiraCallbackHandler


class TestAiraCallbackHandler(unittest.TestCase):
    """Tests for AiraCallbackHandler."""

    def _make_handler(self, **kwargs):
        client = MagicMock()
        defaults = {"client": client, "agent_id": "test-agent"}
        defaults.update(kwargs)
        handler = AiraCallbackHandler(**defaults)
        return handler, client

    # 1. on_tool_end calls notarize with action_type="tool_call"
    def test_on_tool_end_calls_notarize_with_tool_call(self):
        handler, client = self._make_handler()
        handler.on_tool_end("some output", name="search")
        client.notarize.assert_called_once()
        call_kwargs = client.notarize.call_args[1]
        self.assertEqual(call_kwargs["action_type"], "tool_call")

    # 2. on_chain_end calls notarize with action_type="chain_completed"
    def test_on_chain_end_calls_notarize_with_chain_completed(self):
        handler, client = self._make_handler()
        handler.on_chain_end({"output": "hello"})
        client.notarize.assert_called_once()
        call_kwargs = client.notarize.call_args[1]
        self.assertEqual(call_kwargs["action_type"], "chain_completed")

    # 3. on_llm_end calls notarize with action_type="llm_completion"
    def test_on_llm_end_calls_notarize_with_llm_completion(self):
        handler, client = self._make_handler()
        response = MagicMock()
        response.generations = [["gen1"], ["gen2"]]
        handler.on_llm_end(response)
        client.notarize.assert_called_once()
        call_kwargs = client.notarize.call_args[1]
        self.assertEqual(call_kwargs["action_type"], "llm_completion")

    # 4. custom action_types override defaults
    def test_custom_action_types_override_defaults(self):
        handler, client = self._make_handler(
            action_types={"tool_end": "custom_tool"}
        )
        handler.on_tool_end("output", name="calc")
        call_kwargs = client.notarize.call_args[1]
        self.assertEqual(call_kwargs["action_type"], "custom_tool")

    # 5. failure is non-blocking (notarize raises, no exception propagated)
    def test_notarize_failure_is_non_blocking(self):
        handler, client = self._make_handler()
        client.notarize.side_effect = RuntimeError("API down")
        # Should not raise
        handler.on_tool_end("output", name="search")

    # 6. agent_id passed through
    def test_agent_id_passed_through(self):
        handler, client = self._make_handler(agent_id="my-agent")
        handler.on_tool_end("output", name="tool1")
        call_kwargs = client.notarize.call_args[1]
        self.assertEqual(call_kwargs["agent_id"], "my-agent")

    # 7. model_id passed through when set
    def test_model_id_passed_through_when_set(self):
        handler, client = self._make_handler(model_id="gpt-4")
        handler.on_tool_end("output", name="tool1")
        call_kwargs = client.notarize.call_args[1]
        self.assertEqual(call_kwargs["model_id"], "gpt-4")

    # 8. details truncated to 5000 chars
    def test_details_truncated_to_5000_chars(self):
        handler, client = self._make_handler()
        # Create a tool name long enough that the formatted detail exceeds 5000
        long_name = "x" * 6000
        handler.on_tool_end("output", name=long_name)
        call_kwargs = client.notarize.call_args[1]
        self.assertLessEqual(len(call_kwargs["details"]), 5000)

    # 9. no raw output in details (only length)
    def test_no_raw_output_in_details(self):
        handler, client = self._make_handler()
        secret_output = "super_secret_data_12345"
        handler.on_tool_end(secret_output, name="search")
        call_kwargs = client.notarize.call_args[1]
        self.assertNotIn(secret_output, call_kwargs["details"])
        self.assertIn(str(len(secret_output)), call_kwargs["details"])

    # 10. trust_policy enriches details
    def test_trust_policy_enriches_details(self):
        handler, client = self._make_handler(trust_policy={
            "verify_counterparty": True,
            "min_reputation": 60,
        })
        client.get_agent_did.return_value = {"did": "did:web:airaproof.com:agents:search"}
        client.get_reputation.return_value = {"score": 85, "tier": "gold"}
        handler.on_tool_end("output", name="search")
        call_kwargs = client.notarize.call_args[1]
        self.assertIn("trust:", call_kwargs["details"])
        self.assertIn('"did_resolved": true', call_kwargs["details"])
        self.assertIn('"reputation_score": 85', call_kwargs["details"])

    # 11. trust_policy blocks revoked VC
    def test_trust_policy_blocks_revoked_vc(self):
        handler, client = self._make_handler(trust_policy={
            "verify_counterparty": True,
            "require_valid_vc": True,
            "block_revoked_vc": True,
        })
        client.get_agent_did.return_value = {"did": "did:web:airaproof.com:agents:bad"}
        client.get_agent_credential.return_value = {"id": "vc_123"}
        client.verify_credential.return_value = {"valid": False}
        handler.on_tool_end("output", name="bad")
        client.notarize.assert_not_called()

    # 12. trust_policy doesn't block unregistered agents
    def test_trust_policy_doesnt_block_unregistered(self):
        handler, client = self._make_handler(trust_policy={
            "verify_counterparty": True,
            "block_unregistered": False,
        })
        client.get_agent_did.side_effect = Exception("Not found")
        handler.on_tool_end("output", name="unknown-agent")
        client.notarize.assert_called_once()
        call_kwargs = client.notarize.call_args[1]
        self.assertIn('"did_resolved": false', call_kwargs["details"])

    # 13. trust_policy includes reputation warning
    def test_trust_policy_includes_reputation(self):
        handler, client = self._make_handler(trust_policy={
            "verify_counterparty": True,
            "min_reputation": 80,
        })
        client.get_agent_did.return_value = {"did": "did:web:airaproof.com:agents:low"}
        client.get_reputation.return_value = {"score": 45, "tier": "bronze"}
        handler.on_tool_end("output", name="low")
        call_kwargs = client.notarize.call_args[1]
        self.assertIn("reputation_warning", call_kwargs["details"])
        self.assertIn("Below minimum", call_kwargs["details"])

    # 14. no trust_policy means no trust checks
    def test_no_trust_policy_no_checks(self):
        handler, client = self._make_handler()
        handler.on_tool_end("output", name="search")
        client.notarize.assert_called_once()
        call_kwargs = client.notarize.call_args[1]
        self.assertNotIn("trust:", call_kwargs["details"])
        client.get_agent_did.assert_not_called()

    # 15. import error message is clear when langchain not installed
    def test_import_error_message_when_langchain_missing(self):
        # Temporarily remove the mock to simulate missing langchain_core
        saved = {}
        for key in list(sys.modules):
            if key.startswith("langchain_core"):
                saved[key] = sys.modules.pop(key)
        # Also remove the cached aira.extras.langchain module
        saved_aira = sys.modules.pop("aira.extras.langchain", None)

        # Make the import fail
        import builtins
        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "langchain_core.callbacks.base" or name == "langchain_core":
                raise ImportError("No module named 'langchain_core'")
            return real_import(name, *args, **kwargs)

        builtins.__import__ = fake_import
        try:
            with self.assertRaises(ImportError) as ctx:
                import importlib
                importlib.import_module("aira.extras.langchain")
            self.assertIn("pip install aira-sdk[langchain]", str(ctx.exception))
        finally:
            builtins.__import__ = real_import
            # Restore mocks
            sys.modules.update(saved)
            if saved_aira:
                sys.modules["aira.extras.langchain"] = saved_aira


if __name__ == "__main__":
    unittest.main()
