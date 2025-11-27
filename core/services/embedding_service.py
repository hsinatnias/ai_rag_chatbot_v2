try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None


from config.settings import settings


st = None
if SentenceTransformer:
    try:
        st = SentenceTransformer(settings.EMBED_MODEL)
    except Exception:
        st = None


async def embed_text(text: str):
    if st is None:
        return []
    # run in thread in async code where necessary
    return st.encode([text], normalize_embeddings=True)[0].tolist()