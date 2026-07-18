from pathlib import Path


def chunk_text(text: str, size: int = 200) -> list[str]:
    return [text[i:i+size] for i in range(0, len(text), size) if text[i:i+size].strip()]


def load_documents(root: Path) -> list[str]:
    docs = []
    for path in root.glob('**/*.md'):
        if any(part.startswith('.') for part in path.parts):
            continue
        docs.extend(chunk_text(path.read_text(encoding='utf-8')))
    return docs
