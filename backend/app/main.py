from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional

from .schemas import (
    PeerRegisterRequest, PeerHeartbeatRequest, PeerResponse,
    JobCreateRequest, JobUpdateStatusRequest, JobResponse
)
from .registry import Registry

app = FastAPI(
    title="Decentralized GPU P2P Inference Tracker",
    version="0.2.0",
    description="Tracker service for managing peers and inference jobs."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_headers=["*"],
    allow_methods=["*"],
    allow_credentials=True
)

registry = Registry()

@app.get("/health")
def health():
    return {"status": "ok"}

# ---- Peers ---- #
@app.post("/peers/register", response_model=PeerResponse)
def register_peer(payload: PeerRegisterRequest):
    return registry.register_peer(payload)

@app.post("/peers/{peer_id}/heartbeat", response_model=PeerResponse)
def heartbeat(peer_id: str, payload: PeerHeartbeatRequest):
    try:
        return registry.heartbeat(peer_id, payload)
    except KeyError:
        raise HTTPException(status_code=404, detail="Peer not found")

@app.get("/peers", response_model=List[PeerResponse])
def list_peers(only_online: bool = True):
    return registry.list_peers(only_online)

# ---- Jobs ---- #
@app.post("/jobs", response_model=JobResponse)
def create_job(payload: JobCreateRequest):
    if payload.requester_peer_id not in registry.peers:
        raise HTTPException(status_code=400, detail="Requester peer not registered")
    return registry.create_job(payload)

@app.get("/jobs", response_model=List[JobResponse])
def list_jobs():
    return registry.list_jobs()

@app.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str):
    try:
        return registry.get_job(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Job not found")

@app.post("/jobs/{job_id}/status", response_model=JobResponse)
def update_job_status(job_id: str, payload: JobUpdateStatusRequest):
    return registry.update_job_status(job_id, payload)

# ---- Worker Job Fetch ---- #
@app.get("/workers/{peer_id}/next-job", response_model=Optional[JobResponse])
def get_next_job(peer_id: str):
    if peer_id not in registry.peers:
        raise HTTPException(status_code=404, detail="Peer not found")
    job = registry.get_next_assigned_job(peer_id)
    if job:
        return job.to_response()
    return None
