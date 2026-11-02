"""Build a reviewable source ZIP from an explicit public-file allowlist."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[2]
PUBLICOS = (
    "README.md", ".gitignore", "pyproject.toml", "run.ps1",
    "chatbot/*.py", "chatbot/prompt.txt", "chatbot/.env.example",
    "chatbot/data/*.csv", "chatbot/data/*.pdf", "chatbot/tests/test_*.py",
    "chatbot/scripts/*.py", "chatbot/docs/WRITTEN_CASE.md",
    "chatbot/examples/reference/*.md", "chatbot/examples/reference/run.json",
    "ui/*.html", "ui/*.css", "ui/*.js", "ui/README.md",
)


def principal() -> None:
    """Empacota arquivos publicos; exclui segredos, notas locais e resultados privados.
    Package public files; exclude secrets, local notes and private results.
    """
    files = sorted({path for pattern in PUBLICOS for path in ROOT.glob(pattern) if path.is_file()})
    destination = ROOT / "chatbot/private/entrega-final"
    destination.mkdir(parents=True, exist_ok=True)
    manifest = []
    with ZipFile(destination / "emporio-musica-case.zip", "w", ZIP_DEFLATED) as archive:
        for path in files:
            relative = path.relative_to(ROOT).as_posix()
            content = path.read_bytes()
            archive.writestr(relative, content)
            manifest.append({"path": relative, "sha256": hashlib.sha256(content).hexdigest()})
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Packaged {len(files)} public files: {destination / 'emporio-musica-case.zip'}")
    print("Review manifest.json. This is a source archive, not a public Git repository or a live-model evaluation.")


if __name__ == "__main__":
    principal()
