"""Build a reviewable source ZIP from an explicit public-file allowlist."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[2]
PUBLICOS = (
    "README.md", ".gitignore", "pyproject.toml", "requirements.lock", "run.ps1",
    "chatbot/*.py", "chatbot/prompt.txt", "chatbot/.env.example",
    "chatbot/data/*.csv", "chatbot/data/*.pdf", "chatbot/tests/test_*.py",
    "chatbot/scripts/*.py", "chatbot/examples/demonstrations/*.md",
    "chatbot/examples/demonstrations/evidence.json",
    "ui/*.py", "ui/*.html", "ui/*.css", "ui/*.js", "ui/README.md",
    "ui/tests/test_*.py", "output/pdf/*.pdf",
)


def validar_arquivo(path: str, content: bytes) -> None:
    """Fail closed on private paths and recognizable credential literals."""
    parts = Path(path).parts
    if ('private' in parts or '.git' in parts or Path(path).suffix in ('.eml', '.log')
            or (Path(path).name.startswith('.env') and Path(path).name != '.env.example')):
        raise ValueError(f'Private file cannot be packaged: {path}')
    # This complements the allowlist; it is not a universal secret/PII detector.
    if re.search(rb'\b(?:gsk_[A-Za-z0-9]{20,}|AIza[A-Za-z0-9_-]{25,}|sk-(?:proj-)?[A-Za-z0-9_-]{20,})\b', content):
        raise ValueError(f'Possible credential literal in public file: {path}')


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
            validar_arquivo(relative, content)
            archive.writestr(relative, content)
            manifest.append({"path": relative, "sha256": hashlib.sha256(content).hexdigest()})
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Packaged {len(files)} public files: {destination / 'emporio-musica-case.zip'}")
    print("Review manifest.json. This is a source archive, not a public Git repository or a live-model evaluation.")


if __name__ == "__main__":
    principal()
