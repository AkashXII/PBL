import time
import requests
from io import BytesIO
from PIL import Image
import torch
from torchvision import models, transforms

TRACKER_URL = "http://localhost:8000"
PEER_ID = None

# -------- Load Model Once -------- #
device = "cuda" if torch.cuda.is_available() else "cpu"
model = models.resnet50(pretrained=True).to(device).eval()

imagenet_labels = requests.get(
    "https://raw.githubusercontent.com/pytorch/hub/master/imagenet_classes.txt"
).text.splitlines()

preprocess = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])


def register_worker():
    global PEER_ID
    payload = {
        "name": "GPU-Worker-1",
        "host": "localhost",
        "port": 9001,
        "has_gpu": torch.cuda.is_available(),
        "gpu_memory_total_mb": 8000,
        "gpu_memory_free_mb": 6000,
        "models": [{"name": "resnet50", "framework": "pytorch"}]
    }
    resp = requests.post(f"{TRACKER_URL}/peers/register", json=payload)
    PEER_ID = resp.json()["id"]
    print("[REGISTERED] Peer ID:", PEER_ID)


def heartbeat():
    hb = {
        "gpu_memory_free_mb": 5000,
        "current_load_percent": 10
    }
    requests.post(f"{TRACKER_URL}/peers/{PEER_ID}/heartbeat", json=hb)


def poll_jobs():
    resp = requests.get(f"{TRACKER_URL}/workers/{PEER_ID}/next-job")
    if resp.status_code == 200 and resp.json() is not None:
        job = resp.json()
        print("[JOB RECEIVED]", job["id"])
        run_job(job)
    else:
        print("[NO JOB]")


def run_job(job):
    print("[RUNNING] Performing real inference...")

    # download image
    response = requests.get(job["payload_url"])
    img = Image.open(BytesIO(response.content)).convert("RGB")

    batch = preprocess(img).unsqueeze(0).to(device)

    with torch.no_grad():
        outputs = model(batch)
        _, predicted = outputs.max(1)
        label = imagenet_labels[predicted.item()]

    print("[RESULT]:", label)

    update = {
        "status": "COMPLETED",
        "result_url": f"Predicted: {label}"
    }
    requests.post(f"{TRACKER_URL}/jobs/{job['id']}/status", json=update)
    print("[COMPLETED] Job done!")


if __name__ == "__main__":
    register_worker()
    while True:
        heartbeat()
        poll_jobs()
        time.sleep(5)
