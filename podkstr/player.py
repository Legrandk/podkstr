import json
import shutil
import socket
import subprocess

_IPC_SOCK = "/tmp/podkstr-mpv.sock"


def is_mpv_available() -> bool:
    return shutil.which("mpv") is not None


def play(audio_url: str, start_pos: float | None = None) -> subprocess.Popen:
    cmd = [
        "mpv",
        "--referrer=https://www.rtve.es/",
        "--no-video",
        "--really-quiet",
        f"--input-ipc-server={_IPC_SOCK}",
    ]
    if start_pos and start_pos > 0:
        cmd.append(f"--start={start_pos:.1f}")
    cmd.append(audio_url)
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def get_time_pos() -> float | None:
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(1.0)
            s.connect(_IPC_SOCK)
            cmd = json.dumps({"command": ["get_property", "time-pos"]}) + "\n"
            s.sendall(cmd.encode())
            buf = b""
            while b"\n" not in buf:
                chunk = s.recv(4096)
                if not chunk:
                    break
                buf += chunk
            data = json.loads(buf.split(b"\n")[0])
            if data.get("error") == "success":
                return float(data["data"])
    except Exception:
        pass
    return None


def pause() -> None:
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(1.0)
            s.connect(_IPC_SOCK)
            cmd = json.dumps({"command": ["cycle", "pause"]}) + "\n"
            s.sendall(cmd.encode())
    except Exception:
        pass


def seek_to_end() -> None:
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(1.0)
            s.connect(_IPC_SOCK)
            cmd = json.dumps({"command": ["seek", 100, "absolute-percent"]}) + "\n"
            s.sendall(cmd.encode())
    except Exception:
        pass


def seek(seconds: int) -> None:
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(1.0)
            s.connect(_IPC_SOCK)
            cmd = json.dumps({"command": ["seek", seconds, "relative"]}) + "\n"
            s.sendall(cmd.encode())
    except Exception:
        pass
