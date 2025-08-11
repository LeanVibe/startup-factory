from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from routers import api

app = FastAPI(title="MVP API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api.router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "MVP API is running!"}

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": "2025-01-01T00:00:00Z"}
