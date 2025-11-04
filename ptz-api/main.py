from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

origins = [o.strip() for o in os.getenv("CORS_ALLOW_ORIGINS", "").split(",") if o.strip()]
if origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

PTZ_HOST = os.getenv("PTZ_HOST", "192.168.1.50")
PTZ_PORT = int(os.getenv("PTZ_PORT", "80"))
PTZ_USERNAME = os.getenv("PTZ_USERNAME", "admin")
PTZ_PASSWORD = os.getenv("PTZ_PASSWORD", "changeme")
PTZ_PROFILE = os.getenv("PTZ_PROFILE_TOKEN", "Profile_1")
PTZ_TIMEOUT = int(os.getenv("PTZ_TIMEOUT_SEC", "5"))

# Lazy import to avoid startup delays if ONVIF libs are heavy
from onvif import ONVIFCamera

def _client():
    cam = ONVIFCamera(PTZ_HOST, PTZ_PORT, PTZ_USERNAME, PTZ_PASSWORD, wsdl=None)
    media = cam.create_media_service()
    ptz = cam.create_ptz_service()
    return cam, media, ptz

@app.get("/ptz/{camera}/move")
def ptz_move(
    camera: str,
    dir: str = Query(..., regex="^(up|down|left|right|zin|zout)$"),
    speed: float = Query(0.3, ge=0.01, le=1.0),
):
    cam, media, ptz = _client()
    prof = media.GetProfiles()[0]  # or use PTZ_PROFILE
    token = prof.token
    req = ptz.create_type("ContinuousMove")
    req.ProfileToken = token
    req.Velocity = {}
    req.Velocity.PanTilt = {"x": 0.0, "y": 0.0}
    req.Velocity.Zoom = {"x": 0.0}

    if dir == "up":
        req.Velocity.PanTilt["y"] = speed
    elif dir == "down":
        req.Velocity.PanTilt["y"] = -speed
    elif dir == "left":
        req.Velocity.PanTilt["x"] = -speed
    elif dir == "right":
        req.Velocity.PanTilt["x"] = speed
    elif dir == "zin":
        req.Velocity.Zoom["x"] = speed
    elif dir == "zout":
        req.Velocity.Zoom["x"] = -speed

    ptz.ContinuousMove(req)
    return {"ok": True}

@app.get("/ptz/{camera}/stop")
def ptz_stop(camera: str):
    _, media, ptz = _client()
    token = media.GetProfiles()[0].token
    req = ptz.create_type("Stop")
    req.ProfileToken = token
    req.PanTilt = True
    req.Zoom = True
    ptz.Stop(req)
    return {"ok": True}
