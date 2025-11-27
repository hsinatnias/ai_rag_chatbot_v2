# core/pipeline/prompt.py
def build_prompt(question: str, chunks: list, lang: str = "ja"):
    # chunks: list of {"payload": {"text": "...", ...}, "score": 0.9}
    context = "\n\n---\n".join(c["payload"].get("text","") for c in chunks)
    instruction = f"You are a helpful support assistant. Answer concisely in {lang}."
    prompt = f"{instruction}\n\nContext:\n{context}\n\nUser question:\n{question}\n\nAnswer:"
    return prompt
