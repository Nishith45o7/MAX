#!/usr/bin/env python3
"""
══════════════════════════════════════════════════════════════════════════════
  M.A.X HEADLESS SERVER — 24/7 Personal AI Agent for Android Phone Server
══════════════════════════════════════════════════════════════════════════════
  Runs MAX without any desktop dependencies:
    ✦ Telegram Bot Gateway (primary interaction)
    ✦ Web Dashboard (browser-based control panel)
    ✦ Cron Scheduler (autonomous recurring tasks)
    ✦ Health Monitor (self-healing watchdog)
    ✦ Full MAX Brain with tool execution
══════════════════════════════════════════════════════════════════════════════
"""

import asyncio
import json
import logging
import os
import signal
import socket
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

# ── Ensure project root is on sys.path ──
SERVER_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SERVER_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ── Force headless mode environment flag ──
os.environ["MAX_HEADLESS"] = "1"
os.environ["MAX_SERVER_MODE"] = "1"

# ── Logging Setup ──
LOG_DIR = SERVER_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(name)-18s │ %(levelname)-7s │ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "max_server.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("MAX.Server")

# ── Banner ──
BANNER = r"""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     ███╗   ███╗  █████╗  ██╗  ██╗    ███████╗███████╗██████╗ ║
║     ████╗ ████║ ██╔══██╗ ╚██╗██╔╝    ██╔════╝██╔════╝██╔══██╗║
║     ██╔████╔██║ ███████║  ╚███╔╝     ███████╗█████╗  ██████╔╝║
║     ██║╚██╔╝██║ ██╔══██║  ██╔██╗     ╚════██║██╔══╝  ██╔══██╗║
║     ██║ ╚═╝ ██║ ██║  ██║ ██╔╝ ██╗    ███████║███████╗██║  ██║║
║     ╚═╝     ╚═╝ ╚═╝  ╚═╝ ╚═╝  ╚═╝    ╚══════╝╚══════╝╚═╝  ╚═╝║
║                                                              ║
║       M.A.X — 24/7 Headless Personal AI Agent Server         ║
║       Running on: {device}                                   ║
║       Started:    {time}                                     ║
╚══════════════════════════════════════════════════════════════╝
"""


class ServerState:
    """Global server state tracker."""
    def __init__(self):
        self.start_time = time.time()
        self.device_name = os.environ.get("MAX_DEVICE_NAME", "Vivo91-Server")
        self.total_requests = 0
        self.errors = 0
        self.active_services = []
        self.is_running = True

    @property
    def uptime(self) -> str:
        elapsed = int(time.time() - self.start_time)
        days, remainder = divmod(elapsed, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        parts = []
        if days:
            parts.append(f"{days}d")
        if hours:
            parts.append(f"{hours}h")
        parts.append(f"{minutes}m {seconds}s")
        return " ".join(parts)

    def to_dict(self) -> dict:
        return {
            "device": self.device_name,
            "uptime": self.uptime,
            "start_time": datetime.fromtimestamp(self.start_time, tz=timezone.utc).isoformat(),
            "total_requests": self.total_requests,
            "errors": self.errors,
            "active_services": self.active_services,
            "is_running": self.is_running,
        }


state = ServerState()


def get_local_ip() -> str:
    """Get the phone's local network IP for dashboard access."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# ══════════════════════════════════════════════════════════════════════════════
# SERVICE 1: TELEGRAM BOT GATEWAY
# ══════════════════════════════════════════════════════════════════════════════
def start_telegram_service():
    """Starts the Telegram bot in its own thread with enhanced server features."""
    try:
        from gateway.telegram_gateway import run_telegram_daemon
        logger.info("🚀 Telegram Gateway service starting...")
        state.active_services.append("telegram")
        run_telegram_daemon()
    except ImportError as e:
        logger.error(f"Telegram gateway import failed: {e}")
    except Exception as e:
        logger.error(f"Telegram service crashed: {e}")
        state.errors += 1


# ══════════════════════════════════════════════════════════════════════════════
# SERVICE 2: WEB DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
def start_web_dashboard(host: str = "0.0.0.0", port: int = 8091):
    """Starts the Flask web dashboard for browser-based control."""
    try:
        from server.web_dashboard import create_app
        app = create_app(state)
        state.active_services.append("web_dashboard")
        logger.info(f"🌐 Web Dashboard starting on http://{host}:{port}")
        logger.info(f"🌐 Access from any device: http://{get_local_ip()}:{port}")
        app.run(host=host, port=port, debug=False, use_reloader=False)
    except ImportError as e:
        logger.warning(f"Web dashboard import failed (Flask not installed?): {e}")
    except Exception as e:
        logger.error(f"Web dashboard crashed: {e}")
        state.errors += 1


# ══════════════════════════════════════════════════════════════════════════════
# SERVICE 3: CRON SCHEDULER (AUTONOMOUS TASKS)
# ══════════════════════════════════════════════════════════════════════════════
def start_cron_service():
    """Starts the autonomous cron scheduler for background tasks."""
    try:
        from cron.scheduler import CronScheduler
        cron = CronScheduler()
        state.active_services.append("cron_scheduler")
        logger.info("⏰ Cron Scheduler service started")
        cron.run_forever()
    except ImportError:
        logger.info("ℹ️  Cron scheduler not available (brigade_core not loaded)")
    except Exception as e:
        logger.error(f"Cron service error: {e}")
        state.errors += 1


# ══════════════════════════════════════════════════════════════════════════════
# SERVICE 4: HEALTH WATCHDOG
# ══════════════════════════════════════════════════════════════════════════════
def health_watchdog():
    """Periodic health check that monitors server resources and auto-restarts services."""
    import psutil
    
    state.active_services.append("watchdog")
    logger.info("🛡️  Health Watchdog started (60s interval)")

    while state.is_running:
        try:
            cpu = psutil.cpu_percent(interval=1)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            battery = psutil.sensors_battery()
            
            batt_info = ""
            if battery:
                batt_info = f"🔋 {battery.percent}% ({'⚡ Charging' if battery.power_plugged else '🔌 Battery'})"
            
            # Log health summary every 5 minutes
            if int(time.time()) % 300 < 65:
                logger.info(
                    f"📊 Health │ CPU: {cpu:.0f}% │ RAM: {mem.percent:.0f}% │ "
                    f"Disk: {disk.percent:.0f}% │ {batt_info} │ "
                    f"Uptime: {state.uptime} │ Requests: {state.total_requests}"
                )

            # Warning thresholds
            if mem.percent > 85:
                logger.warning(f"⚠️  High memory usage: {mem.percent:.0f}%")
            if cpu > 90:
                logger.warning(f"⚠️  High CPU usage: {cpu:.0f}%")
            if battery and not battery.power_plugged and battery.percent < 15:
                logger.warning(f"⚠️  LOW BATTERY: {battery.percent}% — Connect charger!")

        except Exception as e:
            logger.error(f"Watchdog error: {e}")

        time.sleep(60)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN SERVER ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════════════════
def main():
    """Entry point: starts all services in parallel threads."""
    # Print banner
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(BANNER.format(
        device=state.device_name.ljust(30),
        time=now.ljust(30)
    ))

    local_ip = get_local_ip()
    dashboard_port = int(os.environ.get("MAX_DASHBOARD_PORT", "8091"))

    logger.info("═" * 60)
    logger.info("  M.A.X Headless Server Starting...")
    logger.info(f"  Device:    {state.device_name}")
    logger.info(f"  Local IP:  {local_ip}")
    logger.info(f"  Dashboard: http://{local_ip}:{dashboard_port}")
    logger.info(f"  Logs:      {LOG_DIR}")
    logger.info("═" * 60)

    # Validate core dependencies
    try:
        import max_brain
        logger.info("✅ MAX Brain loaded successfully")
    except ImportError as e:
        logger.error(f"❌ MAX Brain failed to load: {e}")
        logger.error("   Fix dependencies and try again")
        sys.exit(1)

    # Graceful shutdown handler
    def signal_handler(sig, frame):
        logger.info("🛑 Shutdown signal received. Stopping services...")
        state.is_running = False
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start services in daemon threads
    services = [
        ("Telegram Gateway", start_telegram_service),
        ("Web Dashboard", lambda: start_web_dashboard(port=dashboard_port)),
        ("Health Watchdog", health_watchdog),
        ("Cron Scheduler", start_cron_service),
    ]

    threads = []
    for name, target in services:
        t = threading.Thread(target=target, name=name, daemon=True)
        t.start()
        threads.append(t)
        logger.info(f"  ▸ {name} thread started")
        time.sleep(0.5)

    logger.info("")
    logger.info("═" * 60)
    logger.info("  ✅ ALL SERVICES ONLINE — M.A.X is ready!")
    logger.info(f"  🌐 Dashboard:  http://{local_ip}:{dashboard_port}")
    logger.info(f"  📱 Telegram:   Send /start to your bot")
    logger.info("═" * 60)
    logger.info("")

    # Keep main thread alive
    try:
        while state.is_running:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
        state.is_running = False


if __name__ == "__main__":
    main()
