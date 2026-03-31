"""Tests for the MCP server integration."""
from __future__ import annotations

import asyncio
import importlib
import json
import os
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


# Mock mcp at module level so tests run without installing it
_mock_mcp = types.ModuleType("mcp")
_mock_mcp_server = types.ModuleType("mcp.server")
_mock_mcp_types = types.ModuleType("mcp.types")
_mock_mcp_server_stdio = types.ModuleType("mcp.server.stdio")


class _MockServer:
    """Minimal stand-in for mcp.server.Server."""

    def __init__(self, name: str):
        self.name = name
        self._list_tools_handler = None
        self._call_tool_handler = None

    def list_tools(self):
        def decorator(fn):
            self._list_tools_handler = fn
            return fn
        return decorator

    def call_tool(self):
        def decorator(fn):
            self._call_tool_handler = fn
            return fn
        return decorator

    async def run(self, read_stream, write_stream):
        pass


class _MockTool:
    def __init__(self, name, description, inputSchema):
        self.name = name
        self.description = description
        self.inputSchema = inputSchema


class _MockTextContent:
    def __init__(self, type, text):
        self.type = type
        self.text = text


_mock_mcp_server.Server = _MockServer
_mock_mcp_types.Tool = _MockTool
_mock_mcp_types.TextContent = _MockTextContent

sys.modules["mcp"] = _mock_mcp
sys.modules["mcp.server"] = _mock_mcp_server
sys.modules["mcp.types"] = _mock_mcp_types
sys.modules["mcp.server.stdio"] = _mock_mcp_server_stdio


def _run(coro):
    """Helper to run an async function synchronously."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


from aira.extras.mcp import create_server, main


class _FakeReceipt:
    def __init__(self):
        self.id = "act_123"
        self.status = "ok"


class _FakeVerifyResult:
    def __init__(self):
        self.valid = True


class TestMCPServer(unittest.TestCase):
    """Tests for MCP server integration."""

    def _create_server(self, api_key="aira_test_abc123", **kwargs):
        """Create server with a mocked Aira client."""
        mock_client = MagicMock()
        with patch("aira.Aira", return_value=mock_client) as MockAira:
            server = create_server(api_key=api_key, **kwargs)
        return server, mock_client, MockAira

    # 1. create_server returns a Server
    def test_create_server_returns_server(self):
        server, _, _ = self._create_server()
        self.assertIsInstance(server, _MockServer)

    # 2. create_server reads AIRA_API_KEY from env
    def test_create_server_reads_env_key(self):
        with patch.dict(os.environ, {"AIRA_API_KEY": "aira_test_envkey"}, clear=False):
            mock_client = MagicMock()
            with patch("aira.Aira", return_value=mock_client) as MockAira:
                server = create_server()
                MockAira.assert_called_once_with(api_key="aira_test_envkey")

    # 3. create_server raises when no key
    def test_create_server_raises_without_key(self):
        env_backup = os.environ.pop("AIRA_API_KEY", None)
        try:
            with self.assertRaises(ValueError) as ctx:
                create_server(api_key="")
            self.assertIn("API key required", str(ctx.exception))
        finally:
            if env_backup is not None:
                os.environ["AIRA_API_KEY"] = env_backup

    # 4. list_tools returns 3 tools
    def test_list_tools_returns_three_tools(self):
        server, _, _ = self._create_server()
        tools = _run(server._list_tools_handler())
        self.assertEqual(len(tools), 3)

    # 5. tool names are correct
    def test_tool_names_are_correct(self):
        server, _, _ = self._create_server()
        tools = _run(server._list_tools_handler())
        names = {t.name for t in tools}
        self.assertEqual(names, {"notarize_action", "verify_action", "get_receipt"})

    # 6. notarize_action tool calls client.notarize
    def test_notarize_action_calls_client_notarize(self):
        server, mock_client, _ = self._create_server()
        mock_client.notarize.return_value = _FakeReceipt()
        result = _run(server._call_tool_handler(
            "notarize_action",
            {"action_type": "email_sent", "details": "Sent email", "agent_id": "my-agent"},
        ))
        mock_client.notarize.assert_called_once()
        self.assertEqual(len(result), 1)
        data = json.loads(result[0].text)
        self.assertEqual(data["id"], "act_123")

    # 7. verify_action tool calls client.verify_action
    def test_verify_action_calls_client_verify(self):
        server, mock_client, _ = self._create_server()
        mock_client.verify_action.return_value = _FakeVerifyResult()
        result = _run(server._call_tool_handler(
            "verify_action",
            {"action_id": "act_456"},
        ))
        mock_client.verify_action.assert_called_once_with("act_456")
        data = json.loads(result[0].text)
        self.assertTrue(data["valid"])

    # 8. get_receipt tool calls client.get_receipt
    def test_get_receipt_calls_client_get_receipt(self):
        server, mock_client, _ = self._create_server()
        mock_client.get_receipt.return_value = {"receipt_id": "rec_789", "hash": "sha256:abc"}
        result = _run(server._call_tool_handler(
            "get_receipt",
            {"receipt_id": "rec_789"},
        ))
        mock_client.get_receipt.assert_called_once_with("rec_789")
        data = json.loads(result[0].text)
        self.assertEqual(data["receipt_id"], "rec_789")

    # 9. error propagation returns error JSON
    def test_error_returns_error_json(self):
        server, mock_client, _ = self._create_server()
        mock_client.notarize.side_effect = RuntimeError("API exploded")
        result = _run(server._call_tool_handler(
            "notarize_action",
            {"action_type": "test", "details": "test"},
        ))
        data = json.loads(result[0].text)
        self.assertIn("error", data)
        self.assertIn("API exploded", data["error"])

    # 10. main entry point is callable
    def test_main_is_callable(self):
        self.assertTrue(callable(main))

    # 11. main() calls asyncio.run with create_server
    def test_main_calls_asyncio_run(self):
        """main() should call create_server then asyncio.run."""
        mock_server = _MockServer("aira")

        # Mock stdio_server as an async context manager
        class _FakeStdioCtx:
            async def __aenter__(self):
                return (MagicMock(), MagicMock())
            async def __aexit__(self, *args):
                pass

        _mock_mcp_server_stdio.stdio_server = lambda: _FakeStdioCtx()

        with patch("aira.extras.mcp.create_server", return_value=mock_server):
            with patch("asyncio.run") as mock_asyncio_run:
                main()
                mock_asyncio_run.assert_called_once()

    # 12. unknown tool name returns error
    def test_unknown_tool_returns_error(self):
        server, _, _ = self._create_server()
        result = _run(server._call_tool_handler("nonexistent_tool", {}))
        data = json.loads(result[0].text)
        self.assertIn("error", data)
        self.assertIn("Unknown tool", data["error"])

    # 13. base_url is forwarded to Aira client
    def test_base_url_forwarded(self):
        mock_client = MagicMock()
        with patch("aira.Aira", return_value=mock_client) as MockAira:
            create_server(api_key="aira_test_abc123", base_url="http://custom:8080")
            MockAira.assert_called_once_with(api_key="aira_test_abc123", base_url="http://custom:8080")


class TestMCPImportError(unittest.TestCase):
    """Test ImportError when mcp is not installed."""

    def test_import_error_when_mcp_missing(self):
        """Removing mcp from sys.modules should cause ImportError on reimport."""
        # Save current module references
        saved_modules = {}
        mcp_keys = [k for k in sys.modules if k == "mcp" or k.startswith("mcp.")]
        for k in mcp_keys:
            saved_modules[k] = sys.modules.pop(k)

        # Also remove the cached aira.extras.mcp
        saved_aira_mcp = sys.modules.pop("aira.extras.mcp", None)

        try:
            # Patch the import system so 'mcp' cannot be found
            import builtins
            real_import = builtins.__import__

            def _block_mcp(name, *args, **kwargs):
                if name == "mcp" or name.startswith("mcp."):
                    raise ImportError("No module named 'mcp'")
                return real_import(name, *args, **kwargs)

            with patch.object(builtins, "__import__", side_effect=_block_mcp):
                with self.assertRaises(ImportError) as ctx:
                    importlib.import_module("aira.extras.mcp")
                self.assertIn("mcp is required", str(ctx.exception))
        finally:
            # Restore everything
            for k, v in saved_modules.items():
                sys.modules[k] = v
            if saved_aira_mcp is not None:
                sys.modules["aira.extras.mcp"] = saved_aira_mcp


if __name__ == "__main__":
    unittest.main()
