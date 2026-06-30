# import os
# import logging
# from contextlib import asynccontextmanager
# from fastapi import FastAPI, Request, status
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.exceptions import RequestValidationError
# from fastapi.responses import JSONResponse
# from dotenv import load_dotenv

# from backend.database.mongodb import connect_to_mongo, close_mongo_connection
# from backend.api import auth, upload, chat, logs
# from backend.services.logger import setup_logging

# load_dotenv()
# setup_logging()
# logger = logging.getLogger(__name__)

# # Validate required env vars
# required = ["GEMINI_API_KEY", "JWT_SECRET", "MONGODB_URI"]
# for var in required:
#     if not os.getenv(var):
#         raise ValueError(f"Missing required environment variable: {var}")

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     await connect_to_mongo()
#     logger.info("Connected to MongoDB")
#     yield
#     await close_mongo_connection()
#     logger.info("Disconnected from MongoDB")

# app = FastAPI(
#     title="DocuTrust API",
#     description="Enterprise Self-Correcting RAG Platform",
#     version="1.0.0",
#     lifespan=lifespan
# )

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # Change in production
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# @app.exception_handler(RequestValidationError)
# async def validation_exception_handler(request: Request, exc: RequestValidationError):
#     return JSONResponse(
#         status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
#         content={"detail": exc.errors()},
#     )

# app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
# app.include_router(upload.router, prefix="/api/documents", tags=["documents"])
# app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
# app.include_router(logs.router, prefix="/api/logs", tags=["logs"])

# @app.get("/health")
# async def health():
#     return {"status": "ok"}

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=True)



import os
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from backend.database.mongodb import connect_to_mongo, close_mongo_connection
from backend.api import auth, upload, chat, logs
from backend.services.logger import setup_logging

# ----- FORCE LOAD .env FROM PROJECT ROOT -----
project_root = Path(__file__).parent.parent
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)

# DEBUG: Print what we found (remove these later if you want)
print(f"✅ Looking for .env at: {env_path}")
print(f"✅ File exists: {env_path.exists()}")
print(f"✅ JWT_SECRET (from env): {os.getenv('JWT_SECRET', 'NOT SET')}")

# If still not loaded, manually read the file as a last resort
if not os.getenv("JWT_SECRET"):
    print("⚠️  load_dotenv failed – manually reading .env")
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()
        print(f"✅ JWT_SECRET (after manual read): {os.getenv('JWT_SECRET', 'NOT SET')}")
    except Exception as e:
        print(f"❌ Failed to read .env manually: {e}")

# ----- END FORCE LOAD -----

setup_logging()
logger = logging.getLogger(__name__)

# Validate required variables
required = ["GEMINI_API_KEY", "JWT_SECRET", "MONGODB_URI"]
for var in required:
    if not os.getenv(var):
        raise ValueError(f"❌ Missing required environment variable: {var}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    logger.info("Connected to MongoDB")
    yield
    await close_mongo_connection()
    logger.info("Disconnected from MongoDB")

app = FastAPI(
    title="DocuTrust API",
    description="Enterprise Self-Correcting RAG Platform",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(upload.router, prefix="/api/documents", tags=["documents"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(logs.router, prefix="/api/logs", tags=["logs"])

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=True)