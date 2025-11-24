from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class ModelInfo(BaseModel):
    name: str = Field(..., example="resnet50")
    version: Optional[str] = Field(None, example="1.0")
    framework: Optional[str] = Field(None, example="pytorch")  # or tensorflow


class PeerRegisterRequest(BaseModel):
    name: str
    host: str
    port: int
    has_gpu: bool
    gpu_memory_total_mb: Optional[int]
    gpu_memory_free_mb: Optional[int]
    models: List[ModelInfo] = Field(default_factory=list)


class PeerHeartbeatRequest(BaseModel):
    gpu_memory_free_mb: Optional[int] = None
    current_load_percent: Optional[float] = None


class PeerResponse(BaseModel):
    id: str
    name: str
    host: str
    port: int
    has_gpu: bool
    gpu_memory_total_mb: Optional[int]
    gpu_memory_free_mb: Optional[int]
    models: List[ModelInfo]
    is_online: bool


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    ASSIGNED = "ASSIGNED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class JobCreateRequest(BaseModel):
    requester_peer_id: str
    model_name: str
    payload_url: Optional[str] = None


class JobUpdateStatusRequest(BaseModel):
    status: JobStatus
    result_url: Optional[str] = None
    error_message: Optional[str] = None


class JobResponse(BaseModel):
    id: str
    requester_peer_id: str
    assigned_peer_id: Optional[str]
    model_name: str
    status: JobStatus
    payload_url: Optional[str]
    result_url: Optional[str] = None
