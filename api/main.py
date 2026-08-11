from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Candidate Intelligence Platform API",
    description="API for managing candidates, timelines, and hybrid search.",
    version="1.0.0",
)

# Configure CORS
origins = [
    "http://localhost:5173",  # Vite dev server
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from api.routes.candidates import router as candidates_router

@app.get("/health")
def health_check():
    return {"status": "ok"}

app.include_router(candidates_router)

