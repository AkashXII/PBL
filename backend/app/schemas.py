from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class ModelInfo(BaseModel):
    name: str = Field(..., example="resnet50")
    version: Optional[str] = Field(None, example="1.0")
    framework: Optional[str] = Field(None, example="pytorch")  # or tensorflow


class PeerRegisterRequest(BaseModel):
    name: str = Field(..., example="Akash-GPU-PC")
    host: str = Field(..., example="192.168.1.10")
    port: int = Field(..., example=8001)
    has_gpu: bool = Field(..., example=True)
    gpu_memory_total_mb: Optional[int] = Field(None, example=8192)
    gpu_memory_free_mb: Optional[int] = Field(None, example=4096)
    models: List[ModelInfo] = Field(default_factory=list)


class PeerHeartbeatRequest(BaseModel):
    gpu_memory_free_mb: Optional[int] = Field(None, example=4096)
    current_load_percent: Optional[float] = Field(None, ge=0, le=100, example=25.0)


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
    model_name: str = Field(..., example="resnet50")
    payload_url: Optional[str] = Field(
        None,
        example="http://requester-peer:8001/uploads/img123.png"
    )
    # Later: support base64 or other formats


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
