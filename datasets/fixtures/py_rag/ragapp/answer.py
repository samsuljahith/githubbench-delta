from ragapp.retriever import retrieve


def answer_question(query: str, corpus: list[str]) -> str:
    hits = retrieve(query, corpus, k=2)
    if not hits:
        return 'No relevant context found.'
    return 'Based on docs: ' + ' | '.join(hits)
