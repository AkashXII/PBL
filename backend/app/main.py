from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional

from .schemas import (
    PeerRegisterRequest,
    PeerHeartbeatRequest,
    PeerResponse,
    JobCreateRequest,
    JobUpdateStatusRequest,
    JobResponse,
)
from .registry import Registry

app = FastAPI(
    title="Decentralized GPU P2P Inference Tracker",
    version="0.1.0",
    description="Tracker service for managing peers and inference jobs in a P2P GPU network.",
)

# CORS – later we’ll put your React URL here
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # for dev only, restrict in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

registry = Registry()


@app.get("/health", tags=["system"])
def health_check():
    return {"status": "ok"}


# --------- Peer endpoints --------- #

@app.post("/peers/register", response_model=PeerResponse, tags=["peers"])
def register_peer(payload: PeerRegisterRequest):
    return registry.register_peer(payload)


@app.post("/peers/{peer_id}/heartbeat", response_model=PeerResponse, tags=["peers"])
def heartbeat(peer_id: str, payload: PeerHeartbeatRequest):
    try:
        return registry.heartbeat(peer_id, payload)
    except KeyError:
        raise HTTPException(status_code=404, detail="Peer not found")


@app.get("/peers", response_model=List[PeerResponse], tags=["peers"])
def list_peers(only_online: bool = True):
    return registry.list_peers(only_online=only_online)


# --------- Job endpoints --------- #

@app.post("/jobs", response_model=JobResponse, tags=["jobs"])
def create_job(payload: JobCreateRequest):
    # TODO: validate requester_peer_id exists
    if payload.requester_peer_id not in registry.peers:
        raise HTTPException(status_code=400, detail="Requester peer not registered")
    return registry.create_job(payload)


@app.get("/jobs", response_model=List[JobResponse], tags=["jobs"])
def list_jobs():
    return registry.list_jobs()


@app.get("/jobs/{job_id}", response_model=JobResponse, tags=["jobs"])
def get_job(job_id: str):
    try:
        return registry.get_job(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Job not found")


@app.post("/jobs/{job_id}/status", response_model=JobResponse, tags=["jobs"])
def update_job_status(job_id: str, payload: JobUpdateStatusRequest):
    try:
        return registry.update_job_status(job_id, payload)
    except KeyError:
        raise HTTPException(status_code=404, detail="Job not found")
