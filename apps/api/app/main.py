import os
from pathlib import Path

# Load .env file at application startup
env_file = Path(__file__).resolve().parent.parent / ".env"
if env_file.exists():
    with open(env_file, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                val = val.strip().strip("'\"")
                os.environ[key.strip()] = val

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.routers import auth, topology, simulation, templates


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: connect to DB/Redis here
    yield
    # Shutdown: disconnect here

app = FastAPI(
    title="NetSim-Flow API",
    description="Backend API for IP Network Simulation Platform",
    version="0.1.0",
    lifespan=lifespan
)

# Configurazione CORS per permettere al frontend Vite di comunicare
origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(topology.router, prefix="/api/v1")
app.include_router(simulation.router)
app.include_router(templates.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    return {"status": "ok"}
