import os
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from onvif import ONVIFCamera

# -------------------------------------------------
# CORS setup
# -------------------------------------------------
def get_origins():
    val = os.getenv("CORS_ORIGINS", "")
    if not val:
        return ["*"]
    return [o.strip() for o in val.split(",") if o.strip()]

api = FastAPI(title="ONVIF PTZ API", version="1.0.1")
api.add_middleware(
    CORSMiddleware,
    allow_origins=get_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------
# Camera config loader
# -------------------------------------------------
class CamConf:
    def __init__(self, prefix: str):
        self.host = os.getenv(f"{prefix}_HOST")
        self.port = int(os.getenv(f"{prefix}_PORT", "80"))
        self.user = os.getenv(f"{prefix}_USER")
        self.password = os.getenv(f"{prefix}_PASS")
        self.profile_token = os.getenv(f"{prefix}_PROFILE_TOKEN") or None

    def connect(self):
        if not all([self.host, self.user, self.password]):
            raise RuntimeError(f"Incomplete configuration for {self.host=}")
        cam = ONVIFCamera(self.host, self.port, self.user, self.password)
        media = cam.create_media_service()
        profiles = media.GetProfiles()
        token = self.profile_token or profiles[0].token
        ptz = cam.create_ptz_service()
        return cam, ptz, token

# -------------------------------------------------
# Map both original & friendly names
# -------------------------------------------------
CAMS = {
    # Original keys (for backward compat)
    "cam1": CamConf("CAM1"),
    "cam2": CamConf("CAM2"),
    # Friendly aliases matching go2rtc stream names
    "ptz": CamConf("CAM1"),      # 192.168.2.122
    "fixed": CamConf("CAM2"),    # 192.168.2.121
}

# -------------------------------------------------
# Internal helpers
# -------------------------------------------------
def _move(ptz, token, x=0.0, y=0.0, z=0.0, timeout=0):
    req = ptz.create_type("ContinuousMove")
    req.ProfileToken = token
    req.Velocity = {"PanTilt": {"x": x, "y": y}, "Zoom": {"x": z}}
    if timeout:
        req.Timeout = timeout
    ptz.ContinuousMove(req)

def _stop(ptz, token, pan_tilt=True, zoom=True):
    req = ptz.create_type("Stop")
    req.ProfileToken = token
    req.PanTilt = pan_tilt
    req.Zoom = zoom
    ptz.Stop(req)

# -------------------------------------------------
# Routes
# -------------------------------------------------
@api.get("/ptz/{cam}/move")
def ptz_move(
    cam: str,
    dir: str = Query(..., regex="^(up|down|left|right|zoom_in|zoom_out)$"),
    speed: float = Query(0.3, ge=0.05, le=1.0),
):
    if cam not in CAMS:
        raise HTTPException(status_code=404, detail=f"Unknown camera '{cam}'")
    try:
        _, ptz, token = CAMS[cam].connect()
        x = y = z = 0.0
        if dir == "up": y = speed
        elif dir == "down": y = -speed
        elif dir == "left": x = -speed
        elif dir == "right": x = speed
        elif dir == "zoom_in": z = speed
        elif dir == "zoom_out": z = -speed
        _move(ptz, token, x, y, z)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api.get("/ptz/{cam}/stop")
def ptz_stop(cam: str):
    if cam not in CAMS:
        raise HTTPException(status_code=404, detail=f"Unknown camera '{cam}'")
    try:
        _, ptz, token = CAMS[cam].connect()
        _stop(ptz, token, True, True)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api.get("/ptz/{cam}/preset/goto")
def ptz_preset_goto(cam: str, name: Optional[str] = None, token: Optional[str] = None):
    if cam not in CAMS:
        raise HTTPException(status_code=404, detail=f"Unknown camera '{cam}'")
    try:
        camobj, ptz, profile = CAMS[cam].connect()
        pres = ptz.GetPresets({"ProfileToken": profile})
        target = None
        if token:
            target = next((p for p in pres if p.token == token), None)
        elif name:
            target = next((p for p in pres if getattr(p, "Name", None) == name), None)
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
