from sentence_transformers import SentenceTransformer
import numpy as np
import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial

MODEL_NAME = "all-MiniLM-L6-v2"
model = SentenceTransformer(MODEL_NAME)
executor = ThreadPoolExecutor(max_workers=4)

def get_embedding_sync(text: str) -> np.ndarray:
    return model.encode(text, normalize_embeddings=True)

async def get_embedding(text: str) -> np.ndarray:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, get_embedding_sync, text)

async def get_embeddings_batch(texts: list) -> np.ndarray:
    loop = asyncio.get_event_loop()
    encode_func = partial(model.encode, normalize_embeddings=True)
    return await loop.run_in_executor(executor, encode_func, texts)