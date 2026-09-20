"""
Luna JARVIS - Allowlist Module
Controls which system commands Luna can execute.
"""

import os
import subprocess
import logging
import psutil
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("luna.tools.allowlist")


class CommandAllowlist:
    """Whitelist of allowed system commands with execution."""

    def __init__(self, allowed_commands: list = None, log_commands: bool = True):
        self.allowed_commands = allowed_commands or [
            "systeminfo", "screenshot", "listdir", "openapp",
            "volume", "datetime", "timer", "websearch",
            "clipboard", "readfile", "webfetch", "processes",
            "notify", "weather"
        ]
        self.log_commands = log_commands
        self._timers = {}

    def is_allowed(self, command: str) -> bool:
        """Check if a command is in the allowlist."""
        return command in self.allowed_commands

    def execute(self, command: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute an allowed command."""
        if not self.is_allowed(command):
            return {"error": f"Command '{command}' not in allowlist", "allowed": False}

        params = params or {}

        if self.log_commands:
            logger.info(f"Executing: {command}({params})")

        dispatch = {
            "systeminfo": self._systeminfo,
            "screenshot": self._screenshot,
            "listdir": self._listdir,
            "openapp": self._openapp,
            "volume": self._volume,
            "datetime": self._datetime,
            "timer": self._timer,
            "websearch": self._websearch,
            "weather": self._weather,
            "clipboard": self._clipboard,
            "readfile": self._readfile,
            "webfetch": self._webfetch,
            "processes": self._processes,
            "notify": self._notify,
        }

        handler = dispatch.get(command)
        if not handler:
            return {"error": f"No handler for '{command}'"}

        try:
            return handler(**params)
        except Exception as e:
            logger.error(f"Command error: {e}")
            return {"error": str(e)}

    # ── Command Handlers ──────────────────────────────────────────

    def _systeminfo(self, info_type: str = "all") -> Dict[str, Any]:
        """Get system information."""
        result = {}

        if info_type in ("cpu", "all"):
            result["cpu"] = {
                "percent": psutil.cpu_percent(interval=1),
                "count": psutil.cpu_count(),
                "freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
            }

        if info_type in ("ram", "all"):
            mem = psutil.virtual_memory()
            result["ram"] = {
                "total_gb": round(mem.total / (1024**3), 2),
                "used_gb": round(mem.used / (1024**3), 2),
                "percent": mem.percent
            }

        if info_type in ("disk", "all"):
            disk = psutil.disk_usage("C:\\")
            result["disk"] = {
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "percent": disk.percent
            }

        if info_type in ("battery", "all"):
            battery = psutil.sensors_battery()
            if battery:
                result["battery"] = {
                    "percent": battery.percent,
                    "plugged": battery.power_plugged,
                    "secs_left": battery.secsleft if battery.secsleft != psutil.POWER_TIME_UNLIMITED else None
                }
            else:
                result["battery"] = {"status": "no battery detected"}

        return result

    def _screenshot(self, region: str = "full") -> Dict[str, Any]:
        """Take a screenshot."""
        try:
            from PIL import ImageGrab
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = f"screenshots/screenshot_{timestamp}.png"
            Path("screenshots").mkdir(exist_ok=True)

            img = ImageGrab.grab()
            img.save(path)
            return {"path": path, "size": img.size}
        except ImportError:
            return {"error": "Pillow not installed"}

    def _listdir(self, path: str = ".", show_hidden: bool = False) -> Dict[str, Any]:
        """List directory contents."""
        target = Path(path).expanduser()
        if not target.exists():
            return {"error": f"Path not found: {path}"}

        entries = []
        for item in target.iterdir():
            if not show_hidden and item.name.startswith("."):
                continue
            entries.append({
                "name": item.name,
                "type": "dir" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else None
            })

        return {"path": str(target), "entries": entries[:50]}  # Limit to 50

    def _openapp(self, app_name: str) -> Dict[str, Any]:
        """Open an application."""
        # Map common names to executables
        app_map = {
            "chrome": "chrome.exe",
            "firefox": "firefox.exe",
            "notepad": "notepad.exe",
            "explorer": "explorer.exe",
            "cmd": "cmd.exe",
            "powershell": "powershell.exe",
            "vscode": "code",
            "code": "code",
            "intellij": "idea64.exe",
            "pycharm": "pycharm64.exe",
            "spotify": "Spotify.exe",
            "discord": "Discord.exe",
            "steam": "steam.exe",
        }

        exe = app_map.get(app_name.lower(), app_name)

        try:
            subprocess.Popen(exe, shell=True)
            return {"opened": app_name, "executable": exe}
        except Exception as e:
            return {"error": f"Could not open {app_name}: {e}"}

    def _volume(self, action: str = "get", level: Optional[int] = None) -> Dict[str, Any]:
        """Control system volume."""
        try:
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from comtypes import CLSCTX_ALL

            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = interface.QueryInterface(IAudioEndpointVolume)

            if action == "get":
                current = volume.GetMasterVolumeLevelScalar() * 100
                muted = volume.GetMute()
                return {"level": round(current), "muted": bool(muted)}

            elif action == "set" and level is not None:
                volume.SetMasterVolumeLevelScalar(level / 100, None)
                return {"level": level, "set": True}

            elif action == "mute":
                volume.SetMute(True, None)
                return {"muted": True}

            elif action == "unmute":
                volume.SetMute(False, None)
                return {"muted": False}

            elif action == "up":
                current = volume.GetMasterVolumeLevelScalar()
                new_level = min(1.0, current + 0.1)
                volume.SetMasterVolumeLevelScalar(new_level, None)
                return {"level": round(new_level * 100)}

            elif action == "down":
                current = volume.GetMasterVolumeLevelScalar()
                new_level = max(0.0, current - 0.1)
                volume.SetMasterVolumeLevelScalar(new_level, None)
                return {"level": round(new_level * 100)}

        except ImportError:
            return {"error": "pycaw not installed - install with: pip install pycaw"}
        except Exception as e:
            return {"error": str(e)}

    def _datetime(self) -> Dict[str, Any]:
        """Get current date and time."""
        now = datetime.now()
        return {
            "datetime": now.isoformat(),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "day": now.strftime("%A"),
            "timezone": "America/Santiago"
        }

    def _timer(self, duration_seconds: int, label: str = "") -> Dict[str, Any]:
        """Set a timer."""
        import threading

        def timer_callback():
            logger.info(f"Timer done: {label or 'unnamed'}")
            # TODO: send notification to Electron overlay

        timer = threading.Timer(duration_seconds, timer_callback)
        timer.daemon = True
        timer.start()

        return {
            "timer_set": True,
            "duration": duration_seconds,
            "label": label,
            "ends_at": (datetime.now().timestamp() + duration_seconds)
        }


    def _websearch(self, query: str = "", max_results: int = 3) -> Dict[str, Any]:
        """Search the web using a simple approach."""
        try:
            import urllib.request
            import urllib.parse
            import json

            # Use DuckDuckGo instant answer API
            encoded = urllib.parse.quote(query)
            url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1"

            req = urllib.request.Request(url, headers={"User-Agent": "LunaJARVIS/0.1"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            results = []
            if data.get("AbstractText"):
                results.append({
                    "title": data.get("Heading", ""),
                    "text": data["AbstractText"][:300],
                    "source": data.get("AbstractSource", ""),
                    "url": data.get("AbstractURL", ""),
                })

            for topic in data.get("RelatedTopics", [])[:max_results]:
                if isinstance(topic, dict) and "Text" in topic:
                    results.append({
                        "title": topic.get("Text", "")[:80],
                        "text": topic.get("Text", "")[:300],
                        "url": topic.get("FirstURL", ""),
                    })

            return {"query": query, "results": results, "count": len(results)}

        except Exception as e:
            return {"error": f"Web search failed: {e}", "query": query}

    def _weather(self, city: str = "Santiago") -> Dict[str, Any]:
        """Get weather information for a city."""
        try:
            import urllib.request
            import json

            url = f"https://wttr.in/{city}?format=j1"
            req = urllib.request.Request(url, headers={"User-Agent": "LunaJARVIS/0.1"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            current = data.get("current_condition", [{}])[0]
            return {
                "city": city,
                "temp_c": current.get("temp_C", "?"),
                "feels_like_c": current.get("FeelsLikeC", "?"),
                "humidity": current.get("humidity", "?"),
                "description": current.get("lang_es", [{}])[0].get("value", current.get("weatherDesc", [{}])[0].get("value", "")),
                "wind_kmph": current.get("windspeedKmph", "?"),
                "wind_dir": current.get("winddir16Point", "?"),
            }

        except Exception as e:
            return {"error": f"Weather lookup failed: {e}", "city": city}

    def _clipboard(self, action: str = "get", text: str = "") -> Dict[str, Any]:
        """Read or write system clipboard."""
        try:
            import subprocess
            if action == "get":
                result = subprocess.run(
                    ["powershell", "-Command", "Get-Clipboard"],
                    capture_output=True, text=True, timeout=5
                )
                content = result.stdout.strip()
                return {"content": content[:2000], "length": len(content)}
            elif action == "set" and text:
                # Sanitize
                safe_text = text[:5000]
                subprocess.run(
                    ["powershell", "-Command", f"Set-Clipboard -Value '{{}}'".format(safe_text.replace("'", "''"))],
                    capture_output=True, timeout=5
                )
                return {"set": True, "length": len(safe_text)}
            return {"error": "Invalid clipboard action"}
        except Exception as e:
            return {"error": f"Clipboard failed: {e}"}

    def _readfile(self, path: str, max_lines: int = 100, encoding: str = "utf-8") -> Dict[str, Any]:
        """Read text file contents with limits."""
        from pathlib import Path as P
        target = P(path).expanduser()
        if not target.exists():
            return {"error": f"File not found: {path}"}
        if not target.is_file():
            return {"error": f"Not a file: {path}"}
        # Size limit: 512 KB
        if target.stat().st_size > 512 * 1024:
            return {"error": "File too large (max 512 KB)"}
        # Block sensitive files
        blocked_exts = {".key", ".pem", ".env", ".credentials", ".secret"}
        if target.suffix.lower() in blocked_exts:
            return {"error": f"Access to {target.suffix} files is blocked"}
        try:
            with open(target, "r", encoding=encoding, errors="replace") as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= max_lines:
                        break
                    lines.append(line)
            content = "".join(lines)
            return {
                "path": str(target),
                "content": content[:10000],
                "lines_read": len(lines),
                "truncated": len(lines) >= max_lines
            }
        except Exception as e:
            return {"error": f"Read failed: {e}"}

    def _webfetch(self, url: str, max_chars: int = 3000) -> Dict[str, Any]:
        """Fetch content from a URL."""
        try:
            import urllib.request
            import re
            # Only allow http/https
            if not url.startswith(("http://", "https://")):
                return {"error": "Only HTTP/HTTPS URLs allowed"}
            req = urllib.request.Request(url, headers={"User-Agent": "LunaJARVIS/0.1"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                content_type = resp.headers.get("Content-Type", "")
                raw = resp.read(100000)  # max 100KB
                # Try text extraction
                try:
                    text = raw.decode("utf-8", errors="replace")
                except Exception:
                    text = raw.decode("latin-1", errors="replace")
                # Strip HTML tags for readability
                text_clean = re.sub(r'<[^>]+>', ' ', text)
                text_clean = re.sub(r'\s+', ' ', text_clean).strip()
                return {
                    "url": url,
                    "content_type": content_type,
                    "text": text_clean[:max_chars],
                    "total_chars": len(text_clean)
                }
        except Exception as e:
            return {"error": f"Fetch failed: {e}", "url": url}

    def _processes(self, action: str = "list", name: str = "", pid: int = 0) -> Dict[str, Any]:
        """List or get info about running processes."""
        try:
            if action == "list":
                procs = []
                for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
                    try:
                        info = proc.info
                        procs.append({
                            "pid": info["pid"],
                            "name": info["name"],
                            "cpu": round(info["cpu_percent"] or 0, 1),
                            "mem": round(info["memory_percent"] or 0, 1)
                        })
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                # Sort by memory, top 30
                procs.sort(key=lambda x: x["mem"], reverse=True)
                return {"processes": procs[:30], "total": len(procs)}

            elif action == "info" and pid:
                try:
                    proc = psutil.Process(pid)
                    with proc.oneshot():
                        return {
                            "pid": proc.pid,
                            "name": proc.name(),
                            "status": proc.status(),
                            "cpu": proc.cpu_percent(),
                            "mem": round(proc.memory_percent(), 1),
                            "threads": proc.num_threads(),
                            "created": datetime.fromtimestamp(proc.create_time()).isoformat()
                        }
                except psutil.NoSuchProcess:
                    return {"error": f"Process {pid} not found"}

            elif action == "search" and name:
                matches = []
                for proc in psutil.process_iter(["pid", "name"]):
                    try:
                        if name.lower() in proc.info["name"].lower():
                            matches.append({"pid": proc.info["pid"], "name": proc.info["name"]})
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                return {"matches": matches[:20], "query": name}

            return {"error": "Invalid process action. Use: list, info (pid), search (name)"}
        except Exception as e:
            return {"error": f"Process query failed: {e}"}

    def _notify(self, title: str = "Luna", message: str = "", duration: int = 5) -> Dict[str, Any]:
        """Send a desktop notification via PowerShell."""
        try:
            import subprocess
            # Sanitize
            safe_title = title[:100].replace('"', "'").replace('\n', ' ')
            safe_msg = message[:500].replace('"', "'").replace('\n', ' ')
            # Use BurntToast if available, fallback to simple msg
            ps_script = (
                'try { '
                f'New-BurntToastNotification -Text "{safe_title}", "{safe_msg}" '
                '} catch { '
                f'[System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms") | Out-Null; '
                f'[System.Windows.Forms.MessageBox]::Show("{safe_msg}", "{safe_title}", "OK", "Information") '
                '}'
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_script],
                capture_output=True, timeout=10
            )
            return {"notified": True, "title": safe_title, "message": safe_msg}
        except Exception as e:
            return {"error": f"Notification failed: {e}"}


# Singleton
_allowlist: Optional[CommandAllowlist] = None


def get_allowlist() -> CommandAllowlist:
    """Get the singleton command allowlist."""
    global _allowlist
    if _allowlist is None:
        _allowlist = CommandAllowlist()
    return _allowlist
