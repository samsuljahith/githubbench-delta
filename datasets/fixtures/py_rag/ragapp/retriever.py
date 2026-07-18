def score(query: str, chunk: str) -> int:
    q = set(query.lower().split())
    c = set(chunk.lower().split())
    return len(q & c)


def retrieve(query: str, corpus: list[str], k: int = 3) -> list[str]:
    ranked = sorted(corpus, key=lambda ch: score(query, ch), reverse=True)
    return ranked[:k]
