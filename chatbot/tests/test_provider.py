import io
import json
import os
import unittest
import urllib.error
from unittest.mock import patch

from chatbot.agent import Agent, ProviderError
from chatbot.data import Store, localizar_dados
from chatbot.tools import Tools
from chatbot.providers import MODELO, OpenAIProvider, configuracao_provedor, criar_provedor


class ProviderTests(unittest.TestCase):
    def test_agent_roundtrip_preserves_encrypted_reasoning_and_tool_results(self):
        reasoning = {"type": "reasoning", "id": "reason-1", "encrypted_content": "opaque", "summary": []}
        call = {"type": "function_call", "call_id": "hours-1", "name": "consultar_politica",
                "arguments": '{"topic":"hours"}'}
        responses = [
            {"status": "completed", "output": [reasoning, call]},
            {"status": "completed", "output": [
                {"type": "message", "content": [{"type": "output_text", "text": "Store hours checked."}]}]},
        ]
        agent = Agent(Tools(Store(localizar_dados())), OpenAIProvider("local-test"))
        with patch("urllib.request.urlopen", side_effect=[
                io.BytesIO(json.dumps(value).encode()) for value in responses]) as http:
            reply = agent.perguntar("What are the opening hours?")
        continuation = json.loads(http.call_args_list[1].args[0].data)
        self.assertIn(reasoning, continuation["input"])
        self.assertEqual(continuation["input"][-1]["call_id"], "hours-1")
        self.assertIn("09:00", continuation["input"][-1]["output"])
        self.assertEqual(continuation["tool_choice"], "auto")
        self.assertEqual(reply.text, "Store hours checked.")
        self.assertNotIn("encrypted_content", json.dumps(agent.turns))

    def test_wire_payload_and_encrypted_reasoning_continuation(self):
        provider = OpenAIProvider("test-not-a-real-key", MODELO, "medium")
        output = {"status": "completed", "output": []}
        with patch("urllib.request.urlopen", return_value=io.BytesIO(json.dumps(output).encode())) as urlopen:
            provider.responder(instructions="policy", items=[{"role": "user", "content": "hi"}], tool_choice="required")
        request = urlopen.call_args.args[0]
        body = json.loads(request.data)
        self.assertEqual(request.full_url, "https://api.openai.com/v1/responses")
        self.assertEqual(body["model"], MODELO)
        self.assertFalse(body["store"])
        self.assertFalse(body["parallel_tool_calls"])
        self.assertIn("reasoning.encrypted_content", body["include"])
        self.assertEqual(body["reasoning"], {"effort": "medium"})
        self.assertEqual(len(body["tools"]), 7)

    def test_reasoning_can_be_omitted(self):
        with patch("urllib.request.urlopen", return_value=io.BytesIO(b'{"status":"completed","output":[]}')) as urlopen:
            OpenAIProvider("test", MODELO, "").responder(instructions="", items=[], tool_choice="auto")
        self.assertNotIn("reasoning", json.loads(urlopen.call_args.args[0].data))

    def test_error_bodies_and_credentials_are_not_echoed(self):
        error = urllib.error.HTTPError("https://api.openai.com", 401, "secret body", {}, io.BytesIO(b"customer data"))
        with patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(ProviderError) as caught:
                OpenAIProvider("super-secret").responder(instructions="", items=[], tool_choice="auto")
        self.assertIn("401", str(caught.exception))
        for private in ("super-secret", "customer data", "secret body"):
            self.assertNotIn(private, str(caught.exception))

    def test_bad_response_and_network_failure_are_safe(self):
        for effect in (urllib.error.URLError("private detail"), TimeoutError("private detail")):
            with patch("urllib.request.urlopen", side_effect=effect):
                with self.assertRaises(ProviderError) as caught:
                    OpenAIProvider("test").responder(instructions="", items=[], tool_choice="auto")
                self.assertNotIn("private detail", str(caught.exception))
        with patch("urllib.request.urlopen", return_value=io.BytesIO(b"not json")):
            with self.assertRaises(ProviderError):
                OpenAIProvider("test").responder(instructions="", items=[], tool_choice="auto")

    def test_openai_is_default_even_with_unused_gemini_key(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "unused",
                                     "OPENAI_API_KEY": "local-test"}, clear=True):
            settings = configuracao_provedor()
            self.assertEqual(settings["provider"], "openai")
            self.assertEqual(settings["model"], MODELO)
            self.assertEqual(settings["reasoning_effort"], "medium")
            self.assertIsInstance(criar_provedor(), OpenAIProvider)

    def test_missing_openai_key_never_falls_back_to_another_provider(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "unused"}, clear=True):
            with self.assertRaisesRegex(ValueError, "OPENAI_API_KEY"):
                criar_provedor()

    def test_unsupported_models_and_reasoning_are_rejected(self):
        for model in ("gemini-3.5-flash-lite", "gpt-6-sol", ""):
            with self.subTest(model=model), self.assertRaises(ValueError):
                OpenAIProvider("test", model)
        for effort in ("none", "minimal", "invalid"):
            with self.subTest(effort=effort), self.assertRaises(ValueError):
                OpenAIProvider("test", MODELO, effort)
        with patch.dict(os.environ, {"OPENAI_MODEL": "another-model"}, clear=True):
            with self.assertRaises(ValueError):
                configuracao_provedor()

    def test_other_providers_are_rejected_before_any_request(self):
        with patch.dict(os.environ, {'LLM_PROVIDER': 'another-provider', 'OPENAI_API_KEY': 'test'}, clear=True):
            with patch('urllib.request.urlopen') as http:
                with self.assertRaisesRegex(ValueError, 'LLM_PROVIDER must be openai'):
                    criar_provedor()
                http.assert_not_called()

    def test_openai_quota_status_is_preserved_without_exposing_body(self):
        error = urllib.error.HTTPError('https://api.openai.com', 429, '', {}, io.BytesIO(b'private details'))
        with patch('urllib.request.urlopen', side_effect=error):
            with self.assertRaises(ProviderError) as caught:
                OpenAIProvider('test').responder(instructions='', items=[], tool_choice='auto')
        self.assertEqual(caught.exception.status_code, 429)
        self.assertNotIn('private details', str(caught.exception))


if __name__ == "__main__":
    unittest.main()
