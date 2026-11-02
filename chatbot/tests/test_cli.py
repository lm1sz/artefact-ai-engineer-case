import io
import unittest
from unittest.mock import Mock, patch

from chatbot.cli import principal


class CliTests(unittest.TestCase):
    def test_single_question_runs_real_tool_loop_and_exits(self):
        provider = Mock()
        provider.responder.side_effect = [
            {"status": "completed", "output": [
                {"type": "function_call", "call_id": "hours", "name": "consultar_politica",
                 "arguments": '{"topic":"hours"}'}]},
            {"status": "completed", "output": [
                {"type": "message", "content": [{"type": "output_text", "text": "Horários consultados."}]}]},
        ]
        with patch("sys.argv", ["chatbot", "--ask", "Qual o horário?", "--trace"]), \
                patch("chatbot.cli.criar_provedor", return_value=provider), \
                patch("builtins.input", side_effect=AssertionError("Unexpected interactive input")), \
                patch("sys.stdout", new_callable=io.StringIO) as output:
            principal()
        self.assertIn("Horários consultados.", output.getvalue())
        self.assertIn("consultar_politica", output.getvalue())
        self.assertEqual(provider.responder.call_count, 2)

    def test_interactive_reset_and_quit_need_no_model_request(self):
        provider = Mock()
        with patch("sys.argv", ["chatbot"]), \
                patch("chatbot.cli.criar_provedor", return_value=provider), \
                patch("builtins.input", side_effect=["/reset", "/quit"]), \
                patch("sys.stdout", new_callable=io.StringIO) as output:
            principal()
        self.assertIn("Histórico limpo.", output.getvalue())
        provider.responder.assert_not_called()

    def test_empty_single_question_is_rejected_without_entering_interactive_mode(self):
        provider = Mock()
        with patch("sys.argv", ["chatbot", "--ask", ""]), \
                patch("chatbot.cli.criar_provedor", return_value=provider), \
                patch("builtins.input", side_effect=AssertionError("Unexpected interactive input")), \
                patch("sys.stdout", new_callable=io.StringIO) as output:
            principal()
        self.assertIn("4.000 caracteres", output.getvalue())
        provider.responder.assert_not_called()


if __name__ == "__main__":
    unittest.main()
