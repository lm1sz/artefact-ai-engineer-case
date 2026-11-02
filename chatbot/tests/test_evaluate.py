import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from chatbot.scripts.evaluate import verificar_chamadas


class EvaluationTests(unittest.TestCase):
    def test_offline_scenarios_run_without_credentials_or_valid_model_environment(self):
        with tempfile.TemporaryDirectory() as folder:
            env = {**os.environ, "OPENAI_API_KEY": "", "OPENAI_MODEL": "not-a-model"}
            result = subprocess.run([sys.executable, "-X", "utf8", "chatbot/scripts/evaluate.py",
                                     "--offline", "--output", folder],
                                    cwd=Path(__file__).resolve().parents[2], env=env,
                                    capture_output=True, text=True, encoding="utf-8", timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads((Path(folder) / "run.json").read_text(encoding="utf-8"))
            self.assertEqual(report["provider"], "fixture")
            self.assertIsNone(report["model"])
            self.assertEqual(len(report["scenarios"]), 5)
            self.assertEqual(sum(len(s["turns"]) for s in report["scenarios"]), 13)
            for scenario in report["scenarios"]:
                self.assertTrue(scenario["completed"])
                self.assertEqual(scenario["review_flags"], [])
            returns = report["scenarios"][3]["turns"]
            self.assertEqual(returns[-1]["tool_calls"][-1]["result"]["missing"], ["actual receipt date"])
            self.assertTrue(all(turn["tool_calls"][-1]["arguments"]["received_date"] is None for turn in returns))

    def test_evaluation_flags_invented_receipt_even_with_well_typed_arguments(self):
        expected = [("avaliar_devolucao", {"received_date": None})]
        actual = [{"name": "avaliar_devolucao", "arguments": {"received_date": "2025-10-25"},
                   "result": {"outcome": "staff_review"}}]
        self.assertTrue(verificar_chamadas(expected, actual))

    def test_evaluation_requires_explicit_mode_before_any_api_request(self):
        result = subprocess.run([sys.executable, "chatbot/scripts/evaluate.py"],
                                cwd=Path(__file__).resolve().parents[2], capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertIn(b"--offline", result.stderr)
        self.assertIn(b"--live", result.stderr)


if __name__ == "__main__":
    unittest.main()
