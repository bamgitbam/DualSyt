import os
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from onvif import ONVIFCamera

# --------------------------------------------
# CORS
# --------------------------------------------
def get_origins():
    val = os.getenv("CORS_ORIGINS", "")
    return [o.strip() for o in val.split(",") if o.strip()] or ["*"]

api = FastAPI(title="ONVIF PTZ API", version="1.1.0")
api.add_middleware(
    CORSMiddleware,
    allow_origins=get_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------
# Camera config
# --------------------------------------------
class CamConf:
    def __init__(self, prefix: str):
        self.host = os.getenv(f"{prefix}_HOST")
        self.port = int(os.getenv(f"{prefix}_PORT", "80"))
        self.user = os.getenv(f"{prefix}_USER")
        self.password = os.getenv(f"{prefix}_PASS")
        self.profile_token = os.getenv(f"{prefix}_PROFILE_TOKEN") or None

    def connect(self):
        if not all([self.host, self.user, self.password]):
            raise RuntimeError(f"Incomplete configuration (host/user/pass required) for {self.host=}")
        cam = ONVIFCamera(self.host, self.port, self.user, self.password)
        media = cam.create_media_service()
        profiles = media.GetProfiles()
        token = self.profile_token or profiles[0].token
        ptz = cam.create_ptz_service()
        return cam, ptz, token

CAMS = {
    "cam1": CamConf("CAM1"),
    "cam2": CamConf("CAM2"),
    "ptz": CamConf("CAM1"),
    "fixed": CamConf("CAM2"),
}

# --------------------------------------------
# Helpers
# --------------------------------------------
def _move(ptz, token, x=0.0, y=0.0, z=0.0, timeout_ms: int = 0):
    req = ptz.create_type("ContinuousMove")
    req.ProfileToken = token
    req.Velocity = {"PanTilt": {"x": x, "y": y}, "Zoom": {"x": z}}
    if timeout_ms:
        # ONVIF expects an xs:duration; most SDKs accept integer milliseconds
        req.Timeout = timeout_ms
    ptz.ContinuousMove(req)

def _stop(ptz, token, pan_tilt=True, zoom=True):
    req = ptz.create_type("Stop")
    req.ProfileToken = token
    req.PanTilt = pan_tilt
    req.Zoom = zoom
    ptz.Stop(req)

def _get(cam_key: str):
    if cam_key not in CAMS:
        raise HTTPException(status_code=404, detail=f"Unknown camera '{cam_key}'")
    return CAMS[cam_key].connect()

# --------------------------------------------
# Routes
# --------------------------------------------
@api.get("/health")
def health():
    return {"ok": True}

@api.get("/config")
def config():
    # do not expose passwords
    return {
        "cameras": {
            "cam1": {"host": CAMS["cam1"].host, "port": CAMS["cam1"].port, "profile_token": CAMS["cam1"].profile_token},
            "cam2": {"host": CAMS["cam2"].host, "port": CAMS["cam2"].port, "profile_token": CAMS["cam2"].profile_token},
        }
    }

@api.get("/ptz/{cam}/move")
def ptz_move(
    cam: str,
    dir: str = Query(..., pattern=r"^(up|down|left|right|zoom_in|zoom_out|zin|zout)$"),
    speed: float = Query(0.3, ge=0.05, le=1.0),
    duration: int = Query(0, ge=0, description="Move duration in ms; 0 means indefinite (until /stop)"),
):
    try:
        _, ptz, token = _get(cam)
        # Back-compat aliases
        if dir == "zin": dir = "zoom_in"
        if dir == "zout": dir = "zoom_out"

        x = y = z = 0.0
        if dir == "up": y = speed
        elif dir == "down": y = -speed
        elif dir == "left": x = -speed
        elif dir == "right": x = speed
        elif dir == "zoom_in": z = speed
        elif dir == "zoom_out": z = -speed

        _move(ptz, token, x, y, z, timeout_ms=duration if duration > 0 else 0)

        # If a finite duration is requested, send Stop right after ContinuousMove returns.
        # (Many ONVIF stacks respect Timeout, but some require an explicit Stop.)
        if duration > 0:
            _stop(ptz, token, True, True)

        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api.get("/ptz/{cam}/stop")
def ptz_stop(cam: str):
    try:
        _, ptz, token = _get(cam)
        _stop(ptz, token, True, True)
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api.get("/ptz/{cam}/preset/goto")
def ptz_preset_goto(
    cam: str,
    name: Optional[str] = None,
    token: Optional[str] = None,
):
    try:
        camobj, ptz, profile = _get(cam)
        presets = ptz.GetPresets({"ProfileToken": profile})
        target = None
        if token:
            target = next((p for p in presets if p.token == token), None)
        elif name:
            target = next((p for p in presets if getattr(p, "Name", None) == name), None)
        if not target:
            raise HTTPException(404, "Preset not found")
        req = ptz.create_type("GotoPreset")
        req.ProfileToken = profile
        req.PresetToken = target.token
        ptz.GotoPreset(req)
        return {"ok": True, "preset": getattr(target, "Name", None), "token": target.token}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
