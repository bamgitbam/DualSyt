# dualsyt — Dual Streams + ONVIF PTZ (go2rtc + FastAPI)

A minimal, cross-platform viewer that shows **two RTSP streams** (PTZ + fixed) using **go2rtc** and exposes **basic ONVIF PTZ** controls via a tiny **FastAPI** service.  
Tested on desktop (Chromium/Chrome/Safari), iPhone, Samsung/Android, and **Raspberry Pi 5 (64-bit)**.

<p align="right">
  <img src="logo-2.39620a38.png" alt="SYTIS" height="42" />
</p>

---

## Features

- Two simultaneous camera views via go2rtc (`/stream.html?src=...`)  
- ONVIF PTZ: up/down/left/right/zoom+/zoom−/stop (via FastAPI)  
- Simple responsive UI (`ui.html`) you can serve locally  
- Works fully offline on your LAN

---

## Repo Structure

```
.
├─ docker-compose.yml
├─ go2rtc.yaml               # not committed (use go2rtc.yaml.example)
├─ go2rtc.yaml.example       # template with placeholders
├─ ptz-api/
│  ├─ app.py
│  └─ Dockerfile
├─ ui.html
├─ logo-2.39620a38.png
└─ README.md
```

**Security note:** `go2rtc.yaml` contains RTSP URLs with credentials.  
**Do not commit** your real `go2rtc.yaml` — use the included `go2rtc.yaml.example` and add `go2rtc.yaml` to `.gitignore` (already done below).

---

## Quick Start (Linux/macOS)

1) **Create your `go2rtc.yaml` from the template**
```bash
cp go2rtc.yaml.example go2rtc.yaml
# edit with your real camera IPs and credentials
nano go2rtc.yaml
```

2) **Bring up the stack**
```bash
docker compose up -d
docker compose ps
```

3) **Open the streams**
- PTZ view:  `http://localhost:1985/stream.html?src=ptz`  
- Fixed view: `http://localhost:1985/stream.html?src=fixed`

4) **Open the simple UI**
```bash
python3 -m http.server 8090
# then browse http://localhost:8090/ui.html
```

5) **PTZ test (terminal)**
```bash
curl "http://localhost:8089/ptz/ptz/move?dir=right&speed=0.3"
sleep 0.5
curl "http://localhost:8089/ptz/ptz/stop"
```

---

## Raspberry Pi 5 (64-bit) Deploy

1) **Install Docker + Compose plugin**
```bash
sudo apt update
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker "$USER"
newgrp docker
sudo apt install -y docker-compose-plugin
```

2) **Clone & prepare**
```bash
git clone https://github.com/YOUR_GH_USERNAME/dualsyt.git
cd dualsyt
cp go2rtc.yaml.example go2rtc.yaml
nano go2rtc.yaml
```

3) **Adjust CORS (optional)**  
If you’ll open `ui.html` from another device (phone/tablet) on your LAN, add your Pi’s LAN IP origin to `ptz-api` service.

4) **Start services**
```bash
docker compose up -d
docker compose ps
```

5) **Open on LAN devices**
- Streams: `http://<PI_LAN_IP>:1985/stream.html?src=ptz`
- UI: `http://<PI_LAN_IP>:8090/ui.html`
```bash
python3 -m http.server 8090
```

---

## License

MIT (feel free to adapt for your use).


---

## Raspberry Pi 5 Quick Deploy Script

For convenience, you can clone and set up everything on a Pi 5 in one step:

```bash
cat > pi5-deploy.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
sudo apt update
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker "$USER" || true
newgrp docker <<'X'
  sudo apt -y install docker-compose-plugin
  git clone https://github.com/bamgitbam/DualSyt.git ~/DualSyt || true
  cd ~/DualSyt
  [ -f go2rtc.yaml ] || cp go2rtc.yaml.example go2rtc.yaml
  echo ">>> Edit go2rtc.yaml with your RTSP creds, then run: docker compose up -d"
X
EOF
chmod +x pi5-deploy.sh
./pi5-deploy.sh
```

This installs Docker + Compose, clones DualSyt, and prepares your environment automatically.
