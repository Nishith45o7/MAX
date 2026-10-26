"""
Headless WebSocket and HTTP Gateway Server (:7777).
Runs the always-on agent loop, channel listeners, cron scheduler,
and accepts thin client connections.
"""
import os
import sys
import json
import time
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Set
import websockets
from brigade_core import get_state_dir
from brigade_core.config import ConfigManager
from brigade_core.storage import StorageManager
from tideline.engine import TidelineEngine
from agents.registry import AgentRegistry
from agents.org_chart import OrgChart
from cron.scheduler import CronScheduler
from cron.runner import CronRunner

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("gateway")


class GatewayServer:
    """Always-on WebSocket gateway server for Brigade & MAX."""

    def __init__(self, host: str = "127.0.0.1", port: int = 7777, config_mgr: Optional[ConfigManager] = None):
        self.host = host
        self.port = port
        self.config_mgr = config_mgr or ConfigManager()
        self.state_dir = get_state_dir()
        self.storage_mgr = StorageManager(self.state_dir)
        self.agent_registry = AgentRegistry(self.config_mgr, self.storage_mgr)
        self.cron_scheduler = CronScheduler(self.state_dir)
        self.cron_runner = CronRunner(self.cron_scheduler, self.storage_mgr)
        self.active_connections: Set[Any] = set()
        self._server = None
        self._running = False
        self.pid_file = self.state_dir / "gateway.pid"
        self.lock_file = self.state_dir / "gateway.lock"

    def is_token_valid(self, token: Optional[str]) -> bool:
        """Validates token if tokens are configured."""
        cfg = self.config_mgr.load_resolved()
        configured_tokens = cfg.get("gateway", {}).get("tokens", [])
        if not configured_tokens:
            return True  # Open localhost mode
        return token in configured_tokens

    async def handle_connection(self, websocket):
        """Handles incoming client connection and RPC messages."""
        self.active_connections.add(websocket)
        logger.info(f"Client connected from {websocket.remote_address}")

        try:
            async for raw_message in websocket:
                try:
                    data = json.loads(raw_message)
                    resp = await self.dispatch_method(data, websocket)
                    if resp is not None:
                        await websocket.send(json.dumps(resp, ensure_ascii=False))
                except Exception as e:
                    err_resp = {"error": str(e)}
                    await websocket.send(json.dumps(err_resp))
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.active_connections.remove(websocket)
            logger.info("Client disconnected.")

    async def dispatch_method(self, data: Dict[str, Any], websocket) -> Optional[Dict[str, Any]]:
        method = data.get("method")
        params = data.get("params", {})
        msg_id = data.get("id")

        if method == "ping":
            return {"id": msg_id, "result": "pong", "time": time.time()}

        elif method == "status":
            cfg = self.config_mgr.load_resolved()
            return {
                "id": msg_id,
                "result": {
                    "status": "online",
                    "version": "1.0.0",
                    "activeConnections": len(self.active_connections),
                    "agentsCount": len(self.agent_registry.list_agents()),
                    "cronJobsCount": len(self.cron_scheduler.list_jobs()),
                    "port": self.port,
                    "host": self.host
                }
            }

        elif method == "agents/list":
            return {"id": msg_id, "result": self.agent_registry.list_agents()}

        elif method == "cron/list":
            return {"id": msg_id, "result": [j.__dict__ for j in self.cron_scheduler.list_jobs()]}

        elif method == "turn":
            prompt = params.get("prompt", "")
            agent_id = params.get("agent", "main")
            session_id = params.get("session", "main")

            # Stream delta events to client
            await websocket.send(json.dumps({
                "type": "turn_start",
                "agent": agent_id,
                "session": session_id
            }))

            from max_brain import run_agent
            output = run_agent(prompt, session_id=session_id)

            await websocket.send(json.dumps({
                "type": "turn_delta",
                "delta": output
            }))

            return {
                "id": msg_id,
                "result": {
                    "status": "completed",
                    "output": output
                }
            }

        return {"id": msg_id, "error": f"Method '{method}' not recognized"}

    async def run_async(self):
        # Write PID file
        self.pid_file.write_text(str(os.getpid()), encoding="utf-8")
        self.cron_runner.start()
        self._running = True

        logger.info(f"🦁 Brigade Gateway Server listening on ws://{self.host}:{self.port}")
        async with websockets.serve(self.handle_connection, self.host, self.port) as server:
            self._server = server
            await asyncio.Future()  # run forever

    def run(self):
        try:
            asyncio.run(self.run_async())
        except KeyboardInterrupt:
            logger.info("Gateway shutting down...")
        finally:
            self.cron_runner.stop()
            if self.pid_file.exists():
                self.pid_file.unlink(missing_ok=True)


if __name__ == "__main__":
    gw = GatewayServer()
    gw.run()
