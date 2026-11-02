import csv
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from chatbot.data import Store, localizar_dados


class DataTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name) / "data"
        shutil.copytree(localizar_dados(), self.directory)

    def alterar(self, table, change):
        path = self.directory / f"desafio_tecnico_ai_eng - {table}.csv"
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            fields, rows = reader.fieldnames, list(reader)
        change(rows)
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def test_duplicate_product_id_is_rejected_before_dictionary_overwrite(self):
        self.alterar("products", lambda rows: rows.append(rows[0].copy()))
        with self.assertRaisesRegex(ValueError, "duplicate IDs"):
            Store(self.directory)

    def test_unknown_category_is_rejected_on_load(self):
        self.alterar("products", lambda rows: rows[0].update(category_id="999"))
        with self.assertRaisesRegex(ValueError, "category reference"):
            Store(self.directory)

    def test_invalid_price_stock_and_specs_are_rejected(self):
        for change in ({"price_brl": "NaN"}, {"price_brl": "-1"},
                       {"price_brl": "Infinity"}, {"stock_quantity": "-1"}, {"specs": "[]"}):
            with self.subTest(change=change):
                shutil.copyfile(localizar_dados() / "desafio_tecnico_ai_eng - products.csv",
                                self.directory / "desafio_tecnico_ai_eng - products.csv")
                self.alterar("products", lambda rows: rows[0].update(change))
                with self.assertRaises(ValueError):
                    Store(self.directory)

    def test_invalid_promotion_cannot_produce_negative_or_nonfinite_quote(self):
        for value in ("101", "-1", "NaN", "Infinity"):
            with self.subTest(discount=value):
                self.alterar("promotions", lambda rows: rows[0].update(discount_percent=value))
                with self.assertRaises(ValueError):
                    Store(self.directory)

    def test_changed_or_unreadable_pdf_does_not_use_stale_page_mapping(self):
        for texts in (["readable"] * 7, ["readable"] * 7 + [""]):
            with self.subTest(texts=texts):
                store = Store(self.directory)
                pages = [Mock(extract_text=Mock(return_value=text)) for text in texts]
                with patch("pypdf.PdfReader", return_value=Mock(pages=pages)):
                    with self.assertRaisesRegex(ValueError, "eight readable"):
                        _ = store.paginas_politica
                self.assertIsNone(store._policy_pages)


if __name__ == "__main__":
    unittest.main()
