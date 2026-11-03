import unittest

from chatbot.scripts.package_case import validar_arquivo


class DeliveryPackageTests(unittest.TestCase):
    def test_private_paths_are_rejected_even_if_allowlist_changes(self):
        for path in ('chatbot/.env', 'chatbot/.env.backup', 'chatbot/private/run.json',
                     '.git/config', 'recruitment.eml', 'ui-server.log'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                validar_arquivo(path, b'not secret')

    def test_credential_literals_are_rejected_without_printing_them(self):
        for prefix in (b'gsk_', b'AIza', b'sk-proj-'):
            secret = prefix + b'x' * 40
            with self.subTest(prefix=prefix), self.assertRaises(ValueError) as caught:
                validar_arquivo('README.md', secret)
            self.assertNotIn(secret.decode(), str(caught.exception))

    def test_documented_placeholders_and_runtime_configuration_are_allowed(self):
        validar_arquivo('chatbot/.env.example', b'GROQ_API_KEY=\nOPENAI_API_KEY=\n')
        validar_arquivo('README.md', b'GROQ_API_KEY=your-local-groq-key')
