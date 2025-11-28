# scripts/get_embed_dim.py
import asyncio
import sys
from pathlib import Path

# make script runnable directly from project root
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.services.embedder import embed_text

async def main():
    vec = await embed_text("test")
    if not vec:
        print("embed len: 0 (embedder returned empty vector or model not loaded)")
        return
    print("embed len:", len(vec))

if __name__ == "__main__":
    asyncio.run(main())
