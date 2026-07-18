from ragapp.answer import answer_question
from ragapp.ingest import load_documents
from pathlib import Path


def handle(query: str, docs_root: str = 'docs') -> dict:
    corpus = load_documents(Path(docs_root))
    return {'answer': answer_question(query, corpus)}
