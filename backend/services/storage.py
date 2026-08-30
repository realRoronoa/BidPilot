"""Emergent object storage for uploaded PDF binaries. DB stores the reference + extracted pages."""
import os
import requests

STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_UNIVERSAL_KEY") or os.environ.get("EMERGENT_LLM_KEY")
APP_NAME = "bidpilot"

_storage_key = None


LOCAL_STORAGE_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")
os.makedirs(LOCAL_STORAGE_DIR, exist_ok=True)


def init_storage(force: bool = False):
    global _storage_key
    if not EMERGENT_KEY:
        return None
    if _storage_key and not force:
        return _storage_key
    try:
        resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=10)
        if resp.status_code == 200:
            _storage_key = resp.json().get("storage_key")
            return _storage_key
    except Exception:
        pass
    return None


def put_object(path: str, data: bytes, content_type: str = "application/pdf") -> dict:
    try:
        key = init_storage()
        if key:
            resp = requests.put(f"{STORAGE_URL}/objects/{path}",
                                headers={"X-Storage-Key": key, "Content-Type": content_type},
                                data=data, timeout=30)
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass

    # Local fallback
    safe_path = path.replace("/", "_").replace("\\", "_")
    local_file = os.path.join(LOCAL_STORAGE_DIR, safe_path)
    with open(local_file, "wb") as f:
        f.write(data)
    return {"path": safe_path}


def get_object(path: str):
    try:
        key = init_storage()
        if key:
            resp = requests.get(f"{STORAGE_URL}/objects/{path}",
                                headers={"X-Storage-Key": key}, timeout=30)
            if resp.status_code == 200:
                return resp.content, resp.headers.get("Content-Type", "application/pdf")
    except Exception:
        pass

    safe_path = path.replace("/", "_").replace("\\", "_")
    local_file = os.path.join(LOCAL_STORAGE_DIR, safe_path)
    if os.path.exists(local_file):
        with open(local_file, "rb") as f:
            return f.read(), "application/pdf"
    raise FileNotFoundError(f"Object {path} not found")

