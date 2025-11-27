# ingestion/chunker.py
def chunk_text(text: str, max_chars: int = 800, overlap: int = 100):
    chunks = []
    start = 0
    L = len(text)
    while start < L:
        end = min(start + max_chars, L)
        chunk = text[start:end]
        chunks.append(chunk)
        if end == L:
            break
        start = end - overlap
    return chunks
