from __future__ import annotations

from typing import Dict, Optional, List
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from .schemas import (
    PeerRegisterRequest,
    PeerHeartbeatRequest,
    PeerResponse,
    ModelInfo,
    JobCreateRequest,
    JobUpdateStatusRequest,
    JobResponse,
    JobStatus,
)


class Peer:
    def __init__(self, peer_id: str, data: PeerRegisterRequest):
        self.id = peer_id
        self.name = data.name
        self.host = data.host
        self.port = data.port
        self.has_gpu = data.has_gpu
        self.gpu_memory_total_mb = data.gpu_memory_total_mb
        self.gpu_memory_free_mb = data.gpu_memory_free_mb
        self.models: List[ModelInfo] = data.models
        self.current_load_percent: float = 0.0
        self.last_heartbeat: datetime = datetime.now(timezone.utc)
        self.is_online: bool = True

    def to_response(self) -> PeerResponse:
        return PeerResponse(
            id=self.id,
            name=self.name,
            host=self.host,
            port=self.port,
            has_gpu=self.has_gpu,
            gpu_memory_total_mb=self.gpu_memory_total_mb,
            gpu_memory_free_mb=self.gpu_memory_free_mb,
            models=self.models,
            is_online=self.is_online,
        )


class Job:
    def __init__(self, job_id: str, data: JobCreateRequest):
        self.id = job_id
        self.requester_peer_id = data.requester_peer_id
        self.assigned_peer_id: Optional[str] = None
        self.model_name = data.model_name
        self.payload_url = data.payload_url
        self.status: JobStatus = JobStatus.QUEUED
        self.result_url: Optional[str] = None
        self.error_message: Optional[str] = None
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = self.created_at

    def to_response(self) -> JobResponse:
        return JobResponse(
            id=self.id,
            requester_peer_id=self.requester_peer_id,
            assigned_peer_id=self.assigned_peer_id,
            model_name=self.model_name,
            status=self.status,
            payload_url=self.payload_url,
            result_url=self.result_url,
        )


class Registry:
    """
    In-memory registry for peers and jobs.
    Later: replace with proper DB/storage.
    """

    def __init__(self):
        self.peers: Dict[str, Peer] = {}
        self.jobs: Dict[str, Job] = {}

    # -------- Peer management -------- #

    def register_peer(self, data: PeerRegisterRequest) -> PeerResponse:
        peer_id = str(uuid4())
        peer = Peer(peer_id, data)
        self.peers[peer_id] = peer
        return peer.to_response()

    def heartbeat(self, peer_id: str, data: PeerHeartbeatRequest) -> PeerResponse:
        peer = self.peers.get(peer_id)
        if not peer:
            raise KeyError("Peer not found")

        if data.gpu_memory_free_mb is not None:
            peer.gpu_memory_free_mb = data.gpu_memory_free_mb
        if data.current_load_percent is not None:
            peer.current_load_percent = data.current_load_percent

        peer.last_heartbeat = datetime.now(timezone.utc)
        peer.is_online = True
        return peer.to_response()

    def list_peers(self, only_online: bool = True) -> List[PeerResponse]:
        # Mark peers offline if no heartbeat for > 30s (tweak later)
        now = datetime.now(timezone.utc)
        for peer in self.peers.values():
            if now - peer.last_heartbeat > timedelta(seconds=30):
                peer.is_online = False

        peers = self.peers.values()
        if only_online:
            peers = [p for p in peers if p.is_online]
        return [p.to_response() for p in peers]

    # -------- Job management -------- #

    def create_job(self, data: JobCreateRequest) -> JobResponse:
        job_id = str(uuid4())
        job = Job(job_id, data)

        # simple scheduling: pick best peer with required model & free GPU
        peer = self._select_peer_for_model(data.model_name)
        if peer:
            job.assigned_peer_id = peer.id
            job.status = JobStatus.ASSIGNED

        self.jobs[job_id] = job
        return job.to_response()

    def _select_peer_for_model(self, model_name: str) -> Optional[Peer]:
        candidates = []
        for peer in self.peers.values():
            if not peer.is_online or not peer.has_gpu:
                continue
            if any(m.name == model_name for m in peer.models):
                candidates.append(peer)

        if not candidates:
            return None

        # naive heuristic: max free GPU memory, then lowest load
        candidates.sort(
            key=lambda p: (
                -(p.gpu_memory_free_mb or 0),
                p.current_load_percent,
            )
        )
        return candidates[0]

    def get_job(self, job_id: str) -> JobResponse:
        job = self.jobs.get(job_id)
        if not job:
            raise KeyError("Job not found")
        return job.to_response()

    def list_jobs(self) -> List[JobResponse]:
        return [j.to_response() for j in self.jobs.values()]

    def update_job_status(self, job_id: str, data: JobUpdateStatusRequest) -> JobResponse:
        job = self.jobs.get(job_id)
        if not job:
            raise KeyError("Job not found")

        job.status = data.status
        job.result_url = data.result_url
        job.error_message = data.error_message
        job.updated_at = datetime.now(timezone.utc)
        return job.to_response()
