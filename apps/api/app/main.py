from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: connect to DB/Redis here
    yield
    # Shutdown: disconnect here

from app.routers import topology, simulation

app = FastAPI(
    title="NetSim-Flow API",
    description="Backend API for IP Network Simulation Platform",
    version="0.1.0",
    lifespan=lifespan
)

# Configurazione CORS per permettere al frontend Vite di comunicare
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(topology.router, prefix="/api/v1")
app.include_router(simulation.router)

@app.get("/health")
async def health_check():
    return {"status": "ok"}
