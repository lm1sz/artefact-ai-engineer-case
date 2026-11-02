"""Read-only source access. CSV records never become executable instructions."""
from __future__ import annotations

import csv
import json
import re
import unicodedata
from decimal import Decimal, InvalidOperation
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def normalizar_texto(value: str) -> str:
    """Converte para minusculas e remove acentos para comparar termos.
    Lowercase text and remove accents for term matching.
    """
    return "".join(c for c in unicodedata.normalize("NFKD", value.lower())
                   if not unicodedata.combining(c))


def localizar_dados(explicit: str | None = None) -> Path:
    """Usa o diretorio configurado ou os dados locais do chatbot.
    Use the configured directory or the chatbot local data directory.
    """
    if explicit:
        candidate = Path(explicit).expanduser().resolve()
        if not candidate.is_dir():
            raise ValueError("EMPORIO_DATA_DIR must point to the supplied data directory.")
        return candidate
    return ROOT / "data"


class Store:
    def __init__(self, directory: Path):
        """Carrega CSVs e valida relacionamentos; o PDF sera lido sob demanda.
        Load CSVs and validate relationships; read the PDF on demand.
        """
        self.directory = directory
        self.tables = {}
        for name in ("categories", "customers", "products", "orders", "order_items", "promotions"):
            with (directory / f"desafio_tecnico_ai_eng - {name}.csv").open(
                    encoding="utf-8-sig", newline="") as stream:
                self.tables[name] = list(csv.DictReader(stream))
        self._validar_catalogo()
        self.products = {int(r["product_id"]): r for r in self.tables["products"]}
        self.orders = {int(r["order_id"]): r for r in self.tables["orders"]}
        self.categories = {r["category_id"]: r["name"] for r in self.tables["categories"]}
        self.customers = {int(r["customer_id"]): r for r in self.tables["customers"]}
        for table in ("order_items", "promotions"):
            if any(int(r["product_id"]) not in self.products for r in self.tables[table]):
                raise ValueError(f"Broken product reference in {table}.")
        if any(int(r["customer_id"]) not in self.customers for r in self.orders.values()):
            raise ValueError("Broken customer reference in orders.")
        if any(int(r["order_id"]) not in self.orders for r in self.tables["order_items"]):
            raise ValueError("Broken order reference in order_items.")
        self._policy_pages: list[str] | None = None

    def _validar_catalogo(self) -> None:
        """Rejeita IDs duplicados e precos/estoques invalidos antes do atendimento.
        Reject duplicate IDs and invalid prices/stock before serving customers.
        """
        try:
            for table, key in (("categories", "category_id"), ("customers", "customer_id"),
                               ("products", "product_id"), ("orders", "order_id"),
                               ("promotions", "promotion_id")):
                ids = [int(row[key]) for row in self.tables[table]]
                if len(set(ids)) != len(ids) or any(value < 1 for value in ids):
                    raise ValueError(f"Invalid or duplicate IDs in {table}.")
            categories = {row["category_id"] for row in self.tables["categories"]}
            for row in self.tables["products"]:
                price = Decimal(row["price_brl"])
                if not price.is_finite() or price < 0 or int(row["stock_quantity"]) < 0:
                    raise ValueError("Invalid product price or stock.")
                if row["category_id"] not in categories:
                    raise ValueError("Broken category reference in products.")
                if not isinstance(json.loads(row["specs"]), dict):
                    raise ValueError("Product specs must be a JSON object.")
            for row in self.tables["promotions"]:
                discount = Decimal(row["discount_percent"])
                if (not discount.is_finite() or not 0 <= discount <= 100
                        or row["is_active"] not in ("0", "1")):
                    raise ValueError("Invalid promotion discount or active flag.")
        except (KeyError, TypeError, InvalidOperation) as error:
            raise ValueError("Invalid catalog columns or numeric values.") from error

    @property
    def paginas_politica(self) -> list[str]:
        """Extrai o texto do PDF na primeira consulta e guarda as paginas em memoria.
        Extract PDF text on first access and cache its pages in memory.
        """
        if self._policy_pages is None:
            from pypdf import PdfReader
            pages = [re.sub(r"\s+", " ", page.extract_text() or "").strip()
                     for page in PdfReader(self.directory / "políticas_da_loja.pdf").pages]
            # O mapa de assuntos depende das oito paginas desta versao do manual.
            # The topic mapping depends on the eight pages of this manual version.
            if len(pages) != 8 or not all(pages):
                raise ValueError("Expected eight readable policy pages; review the topic mapping.")
            self._policy_pages = pages
        return self._policy_pages

    def mascarar_dados(self, text: str) -> str:
        """Mascara contatos reconhecidos e nomes conhecidos; nao detecta todo dado pessoal.
        Mask recognized contacts and known names; this is not a general personal-data detector.
        """
        for row in self.customers.values():
            for campo, replacement in (("name", row["name"].split()[0] if row["name"].strip() else "[customer]"),
                                       ("email", row["email"][:1] + "***@***"),
                                       ("phone", "(**) *****-XXXX")):
                if row[campo]:
                    text = re.sub(re.escape(row[campo]), lambda _: replacement, text, flags=re.I)
        text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}",
                      lambda m: m[0][0] + "***@***", text)
        text = re.sub(r"(?<!\w)(?:\+55\s*)?(?:\(\d{2}\)|\d{2})[ -]?\d{4,5}[ -]?\d{4}(?!\w)",
                      "(**) *****-XXXX", text)
        return text
