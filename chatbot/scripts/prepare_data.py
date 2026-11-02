"""Create shareable demo inputs without copying original customer contact data."""
from __future__ import annotations

import argparse
import csv
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def preparar_dados(source: Path, target: Path) -> None:
    """Gera dados compartilháveis anonimizados sem modificar os originais.
    Generate anonymized shareable data without changing the originals.
    """
    target.mkdir(parents=True, exist_ok=True)
    known_notes = {
        "", "Pedido cancelado pelo cliente antes do processamento",
        "Item fora de estoque no momento do pedido", "Pagamento não confirmado dentro do prazo",
        "Endereço de entrega inválido informado pelo cliente",
    }
    for name in ("categories", "products", "promotions", "customers", "orders", "order_items"):
        filename = f"desafio_tecnico_ai_eng - {name}.csv"
        with (source / filename).open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            fields = reader.fieldnames
            rows = list(reader)
        if name == "customers":
            rows = [{"customer_id": row["customer_id"], "name": f"Demo {row['customer_id']}",
                     "phone": "", "email": "", "city": ""} for row in rows]
        if name == "orders":
            for row in rows:
                if row["notes"] not in known_notes:
                    row["notes"] = "Requires staff review"
        with (target / filename).open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    shutil.copyfile(source / "políticas_da_loja.pdf", target / "políticas_da_loja.pdf")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Original challenge's data directory")
    parser.add_argument("--target", type=Path, default=ROOT / "data")
    args = parser.parse_args()
    if args.source.resolve() == args.target.resolve():
        parser.error("Source and target must differ; originals must remain intact.")
    preparar_dados(args.source, args.target)
