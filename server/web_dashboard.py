#!/usr/bin/env python3
"""
══════════════════════════════════════════════════════════════════════════════
  M.A.X Web Dashboard — Minimalist, Clean & Mobile-Optimized Control Panel
══════════════════════════════════════════════════════════════════════════════
  Designed specifically for 24/7 phone servers (Vivo 91) and desktop access:
    ✦ Ultra-clean, modern minimalist UI with zero visual clutter
    ✦ Mobile-first responsive design with bottom navigation & app-like feel
    ✦ Full-height Chat Console with quick action prompt pills
    ✦ Real-time hardware telemetry: CPU, RAM, Battery & Charging, Uptime
    ✦ Service health monitor & real-time searchable/filterable log viewer
    ✦ Safe-area insets & tap targets optimized for mobile touchscreens
══════════════════════════════════════════════════════════════════════════════
"""

import json
import logging
import os
import socket
import sys
import time
from datetime import datetime
from pathlib import Path

# Ensure project root is on path
SERVER_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SERVER_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger("MAX.Dashboard")

try:
    from flask import Flask, render_template_string, request, jsonify
except ImportError:
    logger.error("Flask is not installed. Run: pip install flask")
    sys.exit(1)


def get_local_ip() -> str:
    """Retrieve host device's local network IP."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def get_battery_stats():
    """Detect battery info with Linux/Android sysfs fallback for phones."""
    # Try psutil first
    try:
        import psutil
        battery = psutil.sensors_battery()
        if battery is not None:
            return battery.percent, bool(battery.power_plugged)
    except Exception:
        pass

    # Android Termux / Linux sysfs fallback
    try:
        capacity_path = Path("/sys/class/power_supply/battery/capacity")
        status_path = Path("/sys/class/power_supply/battery/status")
        if capacity_path.exists():
            cap = int(capacity_path.read_text().strip())
            charging = False
            if status_path.exists():
                charging = "charging" in status_path.read_text().lower()
            return cap, charging
    except Exception:
        pass

    return None, False


# ══════════════════════════════════════════════════════════════════════════════
# MINIMALIST, MOBILE-FIRST DASHBOARD HTML TEMPLATE
# ══════════════════════════════════════════════════════════════════════════════
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <meta name="theme-color" content="#090a10">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <title>M.A.X — Minimal Dashboard</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-body: #090a10;
            --bg-card: #11141e;
            --bg-card-subtle: #171a26;
            --bg-card-hover: #1c2030;
            --border: rgba(255, 255, 255, 0.08);
            --border-hover: rgba(255, 255, 255, 0.16);
            --accent: #6366f1;
            --accent-glow: rgba(99, 102, 241, 0.2);
            --accent-hover: #4f46e5;
            --success: #10b981;
            --success-glow: rgba(16, 185, 129, 0.2);
            --warning: #f59e0b;
            --danger: #ef4444;
            --text-main: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --radius-lg: 16px;
            --radius-md: 12px;
            --radius-sm: 8px;
            --nav-height: 64px;
            --header-height: 58px;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            -webkit-tap-highlight-color: transparent;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: var(--bg-body);
            color: var(--text-main);
            min-height: 100vh;
            min-height: -webkit-fill-available;
            display: flex;
            flex-direction: column;
            overflow-x: hidden;
            -webkit-font-smoothing: antialiased;
        }

        /* ── Minimal Ambient Background ── */
        .ambient-glow {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background:
                radial-gradient(circle at 10% 0%, rgba(99, 102, 241, 0.05) 0%, transparent 40%),
                radial-gradient(circle at 90% 100%, rgba(16, 185, 129, 0.04) 0%, transparent 40%);
            pointer-events: none;
            z-index: 0;
        }

        /* ── Top Header Bar ── */
        .header {
            position: sticky;
            top: 0;
            z-index: 50;
            height: var(--header-height);
            background: rgba(9, 10, 16, 0.85);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 16px;
        }

        .header-brand {
            display: flex;
            align-items: center;
            gap: 10px;
            text-decoration: none;
            color: inherit;
        }

        .brand-badge {
            width: 32px;
            height: 32px;
            border-radius: var(--radius-sm);
            background: linear-gradient(135deg, var(--accent), #4f46e5);
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 0.95rem;
            color: #ffffff;
            box-shadow: 0 2px 10px var(--accent-glow);
        }

        .brand-info {
            display: flex;
            flex-direction: column;
        }

        .brand-title {
            font-size: 0.95rem;
            font-weight: 700;
            letter-spacing: -0.01em;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .brand-device {
            font-size: 0.72rem;
            color: var(--text-muted);
            font-weight: 500;
        }

        .header-actions {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .status-pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 10px;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            background: rgba(16, 185, 129, 0.1);
            color: var(--success);
            border: 1px solid rgba(16, 185, 129, 0.2);
            transition: all 0.2s ease;
        }

        .status-dot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: var(--success);
            animation: pulse-dot 2s infinite ease-in-out;
        }

        @keyframes pulse-dot {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.4; transform: scale(0.9); }
        }

        .battery-chip {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 4px 8px;
            border-radius: 9999px;
            background: var(--bg-card-subtle);
            border: 1px solid var(--border);
            font-size: 0.75rem;
            color: var(--text-secondary);
            font-weight: 500;
        }

        /* ── Desktop Tab Switcher (Visible on desktop) ── */
        .desktop-nav {
            display: none;
            align-items: center;
            gap: 4px;
            background: var(--bg-card-subtle);
            padding: 3px;
            border-radius: var(--radius-sm);
            border: 1px solid var(--border);
        }

        .desktop-tab {
            padding: 6px 14px;
            font-size: 0.8rem;
            font-weight: 500;
            color: var(--text-secondary);
            border-radius: 6px;
            border: none;
            background: transparent;
            cursor: pointer;
            transition: all 0.15s ease;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .desktop-tab.active {
            background: var(--accent);
            color: #ffffff;
            font-weight: 600;
        }

        /* ── Main Layout Container ── */
        .app-container {
            flex: 1;
            position: relative;
            z-index: 1;
            max-width: 900px;
            width: 100%;
            margin: 0 auto;
            padding: 12px 14px;
            display: flex;
            flex-direction: column;
        }

        /* ── Tab Views ── */
        .tab-content {
            display: none;
            flex-direction: column;
            width: 100%;
            animation: fadeIn 0.2s cubic-bezier(0.16, 1, 0.3, 1);
        }

        .tab-content.active {
            display: flex;
            flex: 1;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(4px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* ── TAB 1: CONSOLE / CHAT ── */
        .chat-view {
            display: flex;
            flex-direction: column;
            height: calc(100vh - var(--header-height) - var(--nav-height) - 24px);
            max-height: calc(100vh - var(--header-height) - var(--nav-height) - 24px);
        }

        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 8px 4px;
            display: flex;
            flex-direction: column;
            gap: 12px;
            scroll-behavior: smooth;
        }

        .chat-messages::-webkit-scrollbar {
            width: 4px;
        }

        .chat-messages::-webkit-scrollbar-thumb {
            background: var(--border);
            border-radius: 4px;
        }

        .chat-bubble {
            max-width: 88%;
            padding: 10px 14px;
            border-radius: var(--radius-md);
            font-size: 0.9rem;
            line-height: 1.5;
            word-break: break-word;
            position: relative;
        }

        .bubble-user {
            align-self: flex-end;
            background: var(--accent);
            color: #ffffff;
            border-bottom-right-radius: 4px;
        }

        .bubble-ai {
            align-self: flex-start;
            background: var(--bg-card);
            border: 1px solid var(--border);
            color: var(--text-main);
            border-bottom-left-radius: 4px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        }

        .bubble-ai pre {
            background: var(--bg-card-subtle);
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            padding: 10px;
            margin: 8px 0;
            overflow-x: auto;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.8rem;
            color: #e2e8f0;
        }

        .bubble-ai code {
            font-family: 'JetBrains Mono', monospace;
            background: var(--bg-card-subtle);
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.82rem;
        }

        .bubble-ai-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 6px;
            padding-bottom: 4px;
            border-bottom: 1px solid rgba(255,255,255,0.05);
            font-size: 0.72rem;
            color: var(--text-muted);
            font-weight: 600;
        }

        .copy-btn {
            background: none;
            border: none;
            color: var(--text-muted);
            cursor: pointer;
            font-size: 0.72rem;
            padding: 2px 6px;
            border-radius: 4px;
            transition: all 0.15s ease;
        }

        .copy-btn:hover {
            color: var(--text-main);
            background: var(--bg-card-subtle);
        }

        .bubble-system {
            align-self: center;
            background: transparent;
            color: var(--text-muted);
            font-size: 0.75rem;
            text-align: center;
            padding: 4px 12px;
            border-radius: 9999px;
            border: 1px dashed var(--border);
            max-width: 90%;
        }

        /* ── Quick Action Chips ── */
        .quick-chips-wrapper {
            overflow-x: auto;
            padding: 8px 0;
            display: flex;
            gap: 6px;
            scrollbar-width: none;
            -ms-overflow-style: none;
        }

        .quick-chips-wrapper::-webkit-scrollbar {
            display: none;
        }

        .chip-btn {
            white-space: nowrap;
            padding: 6px 12px;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 9999px;
            color: var(--text-secondary);
            font-size: 0.78rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.15s ease;
            display: inline-flex;
            align-items: center;
            gap: 5px;
        }

        .chip-btn:hover, .chip-btn:active {
            border-color: var(--accent);
            color: var(--text-main);
            background: var(--bg-card-subtle);
        }

        /* ── Chat Input Bar ── */
        .chat-input-bar {
            display: flex;
            align-items: center;
            gap: 8px;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            padding: 6px 8px 6px 14px;
            transition: border-color 0.2s ease, box-shadow 0.2s ease;
            box-shadow: 0 4px 16px rgba(0,0,0,0.25);
        }

        .chat-input-bar:focus-within {
            border-color: var(--accent);
            box-shadow: 0 0 0 2px var(--accent-glow);
        }

        .chat-input {
            flex: 1;
            background: transparent;
            border: none;
            outline: none;
            color: var(--text-main);
            font-family: inherit;
            font-size: 16px; /* 16px prevents iOS browser auto-zoom */
            line-height: 1.4;
        }

        .chat-input::placeholder {
            color: var(--text-muted);
            font-size: 0.88rem;
        }

        .send-btn {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: var(--accent);
            color: #ffffff;
            border: none;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: transform 0.1s ease, background 0.15s ease;
            flex-shrink: 0;
        }

        .send-btn:active {
            transform: scale(0.92);
        }

        .send-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }

        /* ── TAB 2: MONITOR / STATS ── */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
            margin-bottom: 14px;
        }

        .card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 14px;
            transition: all 0.2s ease;
        }

        .card:hover {
            border-color: var(--border-hover);
        }

        .card-header-flex {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 6px;
        }

        .card-title {
            font-size: 0.74rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .metric-value {
            font-size: 1.45rem;
            font-weight: 700;
            color: var(--text-main);
            letter-spacing: -0.02em;
        }

        .metric-unit {
            font-size: 0.8rem;
            color: var(--text-muted);
            font-weight: 500;
            margin-left: 2px;
        }

        .meter-track {
            height: 5px;
            background: var(--bg-card-subtle);
            border-radius: 9999px;
            overflow: hidden;
            margin-top: 8px;
        }

        .meter-fill {
            height: 100%;
            border-radius: 9999px;
            transition: width 0.6s cubic-bezier(0.16, 1, 0.3, 1), background-color 0.3s ease;
        }

        .meter-accent { background: var(--accent); }
        .meter-success { background: var(--success); }
        .meter-warning { background: var(--warning); }
        .meter-danger { background: var(--danger); }

        /* ── Service Rows List ── */
        .section-label {
            font-size: 0.8rem;
            font-weight: 600;
            color: var(--text-secondary);
            margin: 14px 2px 8px 2px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .service-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .service-item {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            padding: 10px 14px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .service-info {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .service-icon {
            font-size: 1.1rem;
        }

        .service-name {
            font-size: 0.85rem;
            font-weight: 600;
            color: var(--text-main);
        }

        .service-sub {
            font-size: 0.72rem;
            color: var(--text-muted);
        }

        .tag-status {
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 0.72rem;
            font-weight: 600;
        }

        .tag-online {
            background: rgba(16, 185, 129, 0.12);
            color: var(--success);
            border: 1px solid rgba(16, 185, 129, 0.2);
        }

        .tag-offline {
            background: rgba(239, 68, 68, 0.12);
            color: var(--danger);
            border: 1px solid rgba(239, 68, 68, 0.2);
        }

        /* ── Host Device Network Info ── */
        .network-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 12px 14px;
            margin-top: 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 0.82rem;
        }

        .network-details {
            display: flex;
            flex-direction: column;
            gap: 2px;
        }

        .network-title {
            font-weight: 600;
            color: var(--text-main);
        }

        .network-sub {
            color: var(--text-muted);
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem;
        }

        .btn-copy-ip {
            padding: 6px 10px;
            border-radius: 6px;
            border: 1px solid var(--border);
            background: var(--bg-card-subtle);
            color: var(--text-secondary);
            font-size: 0.74rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s ease;
        }

        .btn-copy-ip:hover {
            color: var(--text-main);
            border-color: var(--accent);
        }

        /* ── TAB 3: LOGS VIEWER ── */
        .logs-view {
            display: flex;
            flex-direction: column;
            height: calc(100vh - var(--header-height) - var(--nav-height) - 24px);
            max-height: calc(100vh - var(--header-height) - var(--nav-height) - 24px);
        }

        .logs-toolbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 8px;
            margin-bottom: 8px;
            flex-wrap: wrap;
        }

        .logs-filters {
            display: flex;
            gap: 4px;
        }

        .filter-btn {
            padding: 4px 8px;
            font-size: 0.74rem;
            font-weight: 500;
            border-radius: 6px;
            border: 1px solid var(--border);
            background: var(--bg-card);
            color: var(--text-secondary);
            cursor: pointer;
        }

        .filter-btn.active {
            background: var(--accent);
            color: #ffffff;
            border-color: var(--accent);
        }

        .logs-actions {
            display: flex;
            gap: 6px;
        }

        .action-icon-btn {
            padding: 4px 8px;
            font-size: 0.74rem;
            border-radius: 6px;
            border: 1px solid var(--border);
            background: var(--bg-card);
            color: var(--text-secondary);
            cursor: pointer;
        }

        .action-icon-btn:hover {
            color: var(--text-main);
            border-color: var(--border-hover);
        }

        .logs-box {
            flex: 1;
            background: #06070a;
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 10px;
            overflow-y: auto;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.72rem;
            line-height: 1.6;
            color: #94a3b8;
            white-space: pre-wrap;
            word-break: break-all;
        }

        .log-row {
            padding: 2px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.02);
        }

        .log-error { color: #f87171; }
        .log-warn { color: #fbbf24; }
        .log-info { color: #38bdf8; }
        .log-ok { color: #34d399; }

        /* ── Bottom Navigation Bar (Mobile) ── */
        .bottom-nav {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            height: var(--nav-height);
            background: rgba(9, 10, 16, 0.94);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-top: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: space-around;
            padding: 0 10px calc(env(safe-area-inset-bottom, 0px) + 2px);
            z-index: 50;
        }

        .nav-item {
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 3px;
            color: var(--text-muted);
            text-decoration: none;
            background: transparent;
            border: none;
            padding: 6px 0;
            cursor: pointer;
            transition: color 0.15s ease;
        }

        .nav-item.active {
            color: var(--accent);
        }

        .nav-icon {
            width: 22px;
            height: 22px;
            stroke-width: 2;
        }

        .nav-label {
            font-size: 0.68rem;
            font-weight: 600;
            letter-spacing: 0.02em;
        }

        /* ── Loading Spinner ── */
        .spinner {
            width: 18px;
            height: 18px;
            border: 2px solid rgba(255, 255, 255, 0.2);
            border-top-color: #ffffff;
            border-radius: 50%;
            animation: spin 0.7s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        /* ── Responsive rules for Tablets & Desktops ── */
        @media (min-width: 769px) {
            .desktop-nav {
                display: flex;
            }

            .bottom-nav {
                display: none;
            }

            .app-container {
                padding: 20px;
            }

            .chat-view, .logs-view {
                height: calc(100vh - var(--header-height) - 60px);
                max-height: calc(100vh - var(--header-height) - 60px);
            }

            .stats-grid {
                grid-template-columns: repeat(4, 1fr);
            }
        }
    </style>
</head>
<body>

<div class="ambient-glow"></div>

<!-- Top Header Bar -->
<header class="header">
    <a href="#" class="header-brand" onclick="switchTab('chat'); return false;">
        <div class="brand-badge">M</div>
        <div class="brand-info">
            <span class="brand-title">M.A.X</span>
            <span class="brand-device" id="device-label">{{ device_name }}</span>
        </div>
    </a>

    <!-- Desktop Switcher -->
    <nav class="desktop-nav">
        <button class="desktop-tab active" data-tab="chat" onclick="switchTab('chat')">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
            Console
        </button>
        <button class="desktop-tab" data-tab="stats" onclick="switchTab('stats')">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18"/><path d="M9 21V9"/></svg>
            Monitor
        </button>
        <button class="desktop-tab" data-tab="logs" onclick="switchTab('logs')">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>
            Logs
        </button>
    </nav>

    <div class="header-actions">
        <div class="battery-chip" id="header-battery" style="display: none;">
            <span id="header-battery-icon">🔋</span>
            <span id="header-battery-val">--%</span>
        </div>
        <div class="status-pill" id="status-pill">
            <div class="status-dot"></div>
            <span id="status-text">ONLINE</span>
        </div>
    </div>
</header>

<!-- Main Container -->
<main class="app-container">

    <!-- ═══ TAB 1: CHAT / CONSOLE ═══ -->
    <section class="tab-content active" id="tab-chat">
        <div class="chat-view">
            <!-- Messages stream -->
            <div class="chat-messages" id="chat-messages">
                <div class="chat-bubble bubble-system">
                    M.A.X Brain online on <strong>{{ device_name }}</strong>. Ready for commands.
                </div>
            </div>

            <!-- Quick Action Chips -->
            <div class="quick-chips-wrapper">
                <button class="chip-btn" onclick="sendQuickPrompt('/status')">⚡ Status</button>
                <button class="chip-btn" onclick="sendQuickPrompt('Check battery and system resources')">🔋 Battery</button>
                <button class="chip-btn" onclick="sendQuickPrompt('What is the weather today?')">🌤️ Weather</button>
                <button class="chip-btn" onclick="sendQuickPrompt('What time is it?')">🕒 Time</button>
                <button class="chip-btn" onclick="sendQuickPrompt('/help')">💡 Help</button>
                <button class="chip-btn" onclick="clearChat()">🧹 Clear</button>
            </div>

            <!-- Sticky Input Bar -->
            <div class="chat-input-bar">
                <input
                    type="text"
                    class="chat-input"
                    id="chat-input"
                    placeholder="Ask or command M.A.X..."
                    autocomplete="off"
                    autocorrect="off"
                    autocapitalize="sentences"
                    spellcheck="false"
                >
                <button class="send-btn" id="send-btn" onclick="submitChat()" aria-label="Send">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="22" y1="2" x2="11" y2="13"></line>
                        <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                    </svg>
                </button>
            </div>
        </div>
    </section>

    <!-- ═══ TAB 2: MONITOR / STATS ═══ -->
    <section class="tab-content" id="tab-stats">
        <div class="stats-grid">
            <!-- Uptime Card -->
            <div class="card">
                <div class="card-header-flex">
                    <span class="card-title">⏱️ Uptime</span>
                </div>
                <div class="metric-value" id="val-uptime">--</div>
                <div style="font-size:0.72rem; color:var(--text-muted); margin-top:4px;">Continuous run</div>
            </div>

            <!-- Battery Card -->
            <div class="card">
                <div class="card-header-flex">
                    <span class="card-title">🔋 Battery</span>
                    <span id="battery-status-tag" style="font-size:0.7rem; color:var(--success);">--</span>
                </div>
                <div class="metric-value">
                    <span id="val-battery">--</span><span class="metric-unit">%</span>
                </div>
                <div class="meter-track">
                    <div class="meter-fill meter-success" id="meter-battery" style="width: 0%;"></div>
                </div>
            </div>

            <!-- CPU Card -->
            <div class="card">
                <div class="card-header-flex">
                    <span class="card-title">⚡ CPU Load</span>
                </div>
                <div class="metric-value">
                    <span id="val-cpu">--</span><span class="metric-unit">%</span>
                </div>
                <div class="meter-track">
                    <div class="meter-fill meter-accent" id="meter-cpu" style="width: 0%;"></div>
                </div>
            </div>

            <!-- RAM Card -->
            <div class="card">
                <div class="card-header-flex">
                    <span class="card-title">💾 RAM Usage</span>
                </div>
                <div class="metric-value">
                    <span id="val-ram">--</span><span class="metric-unit">%</span>
                </div>
                <div class="meter-track">
                    <div class="meter-fill meter-accent" id="meter-ram" style="width: 0%;"></div>
                </div>
            </div>
        </div>

        <!-- Requests & Service Counts -->
        <div class="stats-grid" style="margin-bottom: 8px;">
            <div class="card">
                <div class="card-title">📩 Requests Handled</div>
                <div class="metric-value" id="val-requests">0</div>
            </div>
            <div class="card">
                <div class="card-title">🛡️ Active Daemons</div>
                <div class="metric-value" id="val-services">0</div>
            </div>
        </div>

        <!-- System Services -->
        <div class="section-label">
            <span>Daemon Services</span>
            <span style="font-size:0.72rem; color:var(--text-muted);" id="services-sync-time">Live</span>
        </div>

        <div class="service-list">
            <div class="service-item">
                <div class="service-info">
                    <span class="service-icon">🧠</span>
                    <div>
                        <div class="service-name">MAX Brain Core</div>
                        <div class="service-sub">LLM Agent & Actions Engine</div>
                    </div>
                </div>
                <span class="tag-status tag-online" id="svc-brain">ONLINE</span>
            </div>

            <div class="service-item">
                <div class="service-info">
                    <span class="service-icon">🌐</span>
                    <div>
                        <div class="service-name">Web Dashboard API</div>
                        <div class="service-sub">Flask Mobile Gateway</div>
                    </div>
                </div>
                <span class="tag-status tag-online">ONLINE</span>
            </div>

            <div class="service-item">
                <div class="service-info">
                    <span class="service-icon">📱</span>
                    <div>
                        <div class="service-name">Telegram Bot Gateway</div>
                        <div class="service-sub">Remote Messaging Daemon</div>
                    </div>
                </div>
                <span class="tag-status tag-offline" id="svc-telegram">CHECKING</span>
            </div>

            <div class="service-item">
                <div class="service-info">
                    <span class="service-icon">⏰</span>
                    <div>
                        <div class="service-name">Cron Scheduler</div>
                        <div class="service-sub">Automated Periodic Tasks</div>
                    </div>
                </div>
                <span class="tag-status tag-offline" id="svc-cron">CHECKING</span>
            </div>

            <div class="service-item">
                <div class="service-info">
                    <span class="service-icon">🛡️</span>
                    <div>
                        <div class="service-name">Health Watchdog</div>
                        <div class="service-sub">Battery & Thermal Guardian</div>
                    </div>
                </div>
                <span class="tag-status tag-offline" id="svc-watchdog">CHECKING</span>
            </div>
        </div>

        <!-- Network & Device Info -->
        <div class="network-card">
            <div class="network-details">
                <span class="network-title">Local Network IP</span>
                <span class="network-sub" id="local-ip-address">http://{{ local_ip }}:8091</span>
            </div>
            <button class="btn-copy-ip" onclick="copyDashboardUrl()">Copy Link</button>
        </div>
    </section>

    <!-- ═══ TAB 3: LOGS VIEWER ═══ -->
    <section class="tab-content" id="tab-logs">
        <div class="logs-view">
            <div class="logs-toolbar">
                <div class="logs-filters">
                    <button class="filter-btn active" data-filter="all" onclick="filterLogs('all')">All</button>
                    <button class="filter-btn" data-filter="info" onclick="filterLogs('info')">Info</button>
                    <button class="filter-btn" data-filter="warn" onclick="filterLogs('warn')">Warn</button>
                    <button class="filter-btn" data-filter="error" onclick="filterLogs('error')">Error</button>
                </div>
                <div class="logs-actions">
                    <button class="action-icon-btn" onclick="toggleAutoScroll()" id="autoscroll-btn">Auto-scroll: ON</button>
                    <button class="action-icon-btn" onclick="clearLogsUi()">Clear</button>
                    <button class="action-icon-btn" onclick="copyAllLogs()">Copy</button>
                </div>
            </div>
            <div class="logs-box" id="logs-box">
                <div class="log-row log-info">[System] Connecting to M.A.X server logs...</div>
            </div>
        </div>
    </section>

</main>

<!-- Bottom Navigation Bar (Mobile) -->
<nav class="bottom-nav">
    <button class="nav-item active" data-tab="chat" onclick="switchTab('chat')">
        <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
        </svg>
        <span class="nav-label">Console</span>
    </button>
    <button class="nav-item" data-tab="stats" onclick="switchTab('stats')">
        <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <rect x="3" y="3" width="18" height="18" rx="2"/>
            <path d="M3 9h18"/>
            <path d="M9 21V9"/>
        </svg>
        <span class="nav-label">Monitor</span>
    </button>
    <button class="nav-item" data-tab="logs" onclick="switchTab('logs')">
        <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <polyline points="4 17 10 11 4 5"/>
            <line x1="12" y1="19" x2="20" y2="19"/>
        </svg>
        <span class="nav-label">Logs</span>
    </button>
</nav>

<script>
    // State
    let currentTab = 'chat';
    let rawLogLines = [];
    let currentLogFilter = 'all';
    let autoScrollLogs = true;
    let isSendingChat = false;

    // Tab Switching
    function switchTab(tabId) {
        currentTab = tabId;

        // Switch Tab views
        document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
        const targetTab = document.getElementById('tab-' + tabId);
        if (targetTab) targetTab.classList.add('active');

        // Switch Mobile Nav
        document.querySelectorAll('.bottom-nav .nav-item').forEach(el => {
            el.classList.toggle('active', el.dataset.tab === tabId);
        });

        // Switch Desktop Nav
        document.querySelectorAll('.desktop-nav .desktop-tab').forEach(el => {
            el.classList.toggle('active', el.dataset.tab === tabId);
        });

        // Haptic feedback if supported on mobile
        if (navigator.vibrate) navigator.vibrate(12);

        // Instant refresh on tab activation
        if (tabId === 'stats') refreshStats();
        if (tabId === 'logs') refreshLogs();
        if (tabId === 'chat') {
            const box = document.getElementById('chat-messages');
            box.scrollTop = box.scrollHeight;
        }
    }

    // Polling Stats
    async function refreshStats() {
        try {
            const res = await fetch('/api/status');
            if (!res.ok) throw new Error('Status error');
            const data = await res.json();

            // Status indicator
            document.getElementById('status-text').textContent = 'ONLINE';
            document.getElementById('status-pill').style.color = 'var(--success)';
            document.getElementById('status-pill').style.borderColor = 'rgba(16, 185, 129, 0.2)';

            // Metrics
            document.getElementById('val-uptime').textContent = data.uptime || '--';
            document.getElementById('val-cpu').textContent = data.cpu !== undefined ? Math.round(data.cpu) : '--';
            document.getElementById('val-ram').textContent = data.ram !== undefined ? Math.round(data.ram) : '--';
            document.getElementById('val-requests').textContent = data.total_requests || 0;
            document.getElementById('val-services').textContent = (data.active_services || []).length;

            // Meters
            const cpu = data.cpu || 0;
            const cpuMeter = document.getElementById('meter-cpu');
            cpuMeter.style.width = Math.min(cpu, 100) + '%';
            cpuMeter.className = 'meter-fill ' + (cpu > 80 ? 'meter-danger' : cpu > 50 ? 'meter-warning' : 'meter-accent');

            const ram = data.ram || 0;
            const ramMeter = document.getElementById('meter-ram');
            ramMeter.style.width = Math.min(ram, 100) + '%';
            ramMeter.className = 'meter-fill ' + (ram > 85 ? 'meter-danger' : ram > 65 ? 'meter-warning' : 'meter-accent');

            // Battery
            if (data.battery !== undefined && data.battery !== null) {
                const battVal = Math.round(data.battery);
                document.getElementById('val-battery').textContent = battVal;
                const charging = data.battery_charging;
                document.getElementById('battery-status-tag').textContent = charging ? '⚡ Charging' : 'Discharging';

                const battMeter = document.getElementById('meter-battery');
                battMeter.style.width = battVal + '%';
                battMeter.className = 'meter-fill ' + (battVal <= 20 ? 'meter-danger' : battVal <= 40 ? 'meter-warning' : 'meter-success');

                // Header battery badge
                const hb = document.getElementById('header-battery');
                hb.style.display = 'inline-flex';
                document.getElementById('header-battery-val').textContent = (charging ? '⚡ ' : '') + battVal + '%';
            }

            // Services
            const svcs = data.active_services || [];
            ['telegram', 'cron', 'watchdog'].forEach(svc => {
                const el = document.getElementById('svc-' + svc);
                if (el) {
                    const active = svcs.includes(svc) || svcs.includes(svc + '_scheduler') || svcs.includes('cron_scheduler');
                    el.textContent = active ? 'ONLINE' : 'OFFLINE';
                    el.className = 'tag-status ' + (active ? 'tag-online' : 'tag-offline');
                }
            });

            // Local IP
            if (data.local_ip) {
                document.getElementById('local-ip-address').textContent = 'http://' + data.local_ip + ':8091';
            }

        } catch (e) {
            document.getElementById('status-text').textContent = 'RECONNECTING';
            document.getElementById('status-pill').style.color = 'var(--warning)';
            document.getElementById('status-pill').style.borderColor = 'rgba(245, 158, 11, 0.2)';
        }
    }

    // Chat Functions
    async function submitChat() {
        const input = document.getElementById('chat-input');
        const text = input.value.trim();
        if (!text || isSendingChat) return;

        input.value = '';
        appendMessage(text, 'user');

        const sendBtn = document.getElementById('send-btn');
        sendBtn.disabled = true;
        isSendingChat = true;
        sendBtn.innerHTML = '<div class="spinner"></div>';

        try {
            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            });

            const data = await res.json();
            appendMessage(data.reply || 'No response returned from M.A.X.', 'ai');
        } catch (err) {
            appendMessage('⚠️ Connection error: ' + err.message, 'system');
        } finally {
            sendBtn.disabled = false;
            isSendingChat = false;
            sendBtn.innerHTML = `
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="22" y1="2" x2="11" y2="13"></line>
                    <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                </svg>`;
            input.focus();
        }
    }

    function sendQuickPrompt(promptText) {
        document.getElementById('chat-input').value = promptText;
        submitChat();
    }

    function appendMessage(text, type) {
        const container = document.getElementById('chat-messages');
        const bubble = document.createElement('div');
        bubble.className = 'chat-bubble bubble-' + type;

        if (type === 'ai') {
            const header = document.createElement('div');
            header.className = 'bubble-ai-header';
            header.innerHTML = `<span>M.A.X</span><button class="copy-btn" onclick="copyText(this)">Copy</button>`;
            bubble.appendChild(header);

            // Format markdown basics (code blocks, inline code, bold)
            const content = document.createElement('div');
            content.innerHTML = formatMarkdown(text);
            bubble.appendChild(content);
        } else {
            bubble.textContent = text;
        }

        container.appendChild(bubble);
        container.scrollTop = container.scrollHeight;
    }

    function formatMarkdown(text) {
        if (!text) return '';
        // Escape HTML
        let escaped = text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');

        // Multi-line code blocks: ```code```
        escaped = escaped.replace(/```([\\s\\S]*?)```/g, '<pre><code>$1</code></pre>');
        // Inline code: `code`
        escaped = escaped.replace(/`([^`]+)`/g, '<code>$1</code>');
        // Bold: **text**
        escaped = escaped.replace(/\\*\\*([^\\*]+)\\*\\*/g, '<strong>$1</strong>');
        // Preserve newlines
        escaped = escaped.replace(/\\n/g, '<br>');

        return escaped;
    }

    function copyText(btn) {
        const bubble = btn.closest('.chat-bubble');
        const content = bubble.innerText.replace(/^M\\.A\\.XCopy\\n/, '').trim();
        navigator.clipboard.writeText(content).then(() => {
            btn.textContent = 'Copied!';
            setTimeout(() => { btn.textContent = 'Copy'; }, 1800);
        });
    }

    function clearChat() {
        const container = document.getElementById('chat-messages');
        container.innerHTML = `
            <div class="chat-bubble bubble-system">
                Console cleared. M.A.X ready for commands.
            </div>`;
    }

    document.getElementById('chat-input').addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            submitChat();
        }
    });

    // Logs Handling
    async function refreshLogs() {
        try {
            const res = await fetch('/api/logs');
            if (!res.ok) return;
            const data = await res.json();
            rawLogLines = data.lines || [];
            renderLogs();
        } catch (e) {}
    }

    function renderLogs() {
        const box = document.getElementById('logs-box');
        box.innerHTML = '';

        const filtered = rawLogLines.filter(line => {
            if (currentLogFilter === 'all') return true;
            const l = line.toLowerCase();
            if (currentLogFilter === 'info') return l.includes('info') || l.includes('online') || l.includes('✅');
            if (currentLogFilter === 'warn') return l.includes('warn') || l.includes('⚠️');
            if (currentLogFilter === 'error') return l.includes('error') || l.includes('fail') || l.includes('❌');
            return true;
        });

        if (filtered.length === 0) {
            box.innerHTML = '<div class="log-row" style="color:var(--text-muted)">No log entries found for this filter.</div>';
            return;
        }

        filtered.forEach(line => {
            const row = document.createElement('div');
            row.className = 'log-row';
            const lower = line.toLowerCase();
            if (lower.includes('error') || lower.includes('fail') || lower.includes('❌')) {
                row.className += ' log-error';
            } else if (lower.includes('warn') || lower.includes('⚠️')) {
                row.className += ' log-warn';
            } else if (lower.includes('info') || lower.includes('started') || lower.includes('✅')) {
                row.className += ' log-info';
            }
            row.textContent = line;
            box.appendChild(row);
        });

        if (autoScrollLogs) {
            box.scrollTop = box.scrollHeight;
        }
    }

    function filterLogs(filterType) {
        currentLogFilter = filterType;
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.filter === filterType);
        });
        renderLogs();
    }

    function toggleAutoScroll() {
        autoScrollLogs = !autoScrollLogs;
        const btn = document.getElementById('autoscroll-btn');
        btn.textContent = 'Auto-scroll: ' + (autoScrollLogs ? 'ON' : 'OFF');
        if (autoScrollLogs) {
            const box = document.getElementById('logs-box');
            box.scrollTop = box.scrollHeight;
        }
    }

    function clearLogsUi() {
        rawLogLines = ['[System] Logs view cleared.'];
        renderLogs();
    }

    function copyAllLogs() {
        const text = rawLogLines.join('\\n');
        navigator.clipboard.writeText(text).then(() => {
            alert('Logs copied to clipboard');
        });
    }

    function copyDashboardUrl() {
        const url = document.getElementById('local-ip-address').textContent;
        navigator.clipboard.writeText(url).then(() => {
            alert('Dashboard URL copied: ' + url);
        });
    }

    // Auto-refresh loops
    refreshStats();
    setInterval(refreshStats, 4000);
    setInterval(() => {
        if (currentTab === 'logs') refreshLogs();
    }, 5000);
</script>

</body>
</html>
"""


# ══════════════════════════════════════════════════════════════════════════════
# FLASK APPLICATION FACTORY
# ══════════════════════════════════════════════════════════════════════════════
def create_app(server_state=None):
    """Creates and configures the Flask dashboard application."""
    app = Flask(__name__)
    app.config['JSON_SORT_KEYS'] = False

    # ── Routes ──
    @app.route("/")
    def index():
        device = server_state.device_name if server_state else "Vivo91-Server"
        local_ip = get_local_ip()
        return render_template_string(DASHBOARD_HTML, device_name=device, local_ip=local_ip)

    @app.route("/api/status")
    def api_status():
        data = server_state.to_dict() if server_state else {}
        data["local_ip"] = get_local_ip()

        try:
            import psutil
            data["cpu"] = psutil.cpu_percent(interval=None)
            data["ram"] = psutil.virtual_memory().percent
        except Exception:
            data["cpu"] = 0
            data["ram"] = 0

        # Battery check with phone sysfs fallback
        batt_percent, batt_charging = get_battery_stats()
        data["battery"] = batt_percent
        data["battery_charging"] = batt_charging

        return jsonify(data)

    @app.route("/api/chat", methods=["POST"])
    def api_chat():
        try:
            body = request.get_json(force=True)
            message = body.get("message", "").strip()
            if not message:
                return jsonify({"reply": "Empty message."}), 400

            import max_brain
            if server_state:
                server_state.total_requests += 1

            reply = max_brain.run_agent(message, session_id="dashboard", origin="dashboard")
            return jsonify({"reply": reply})
        except Exception as e:
            logger.error(f"Chat API error: {e}")
            if server_state:
                server_state.errors += 1
            return jsonify({"reply": f"Error: {str(e)}"}), 500

    @app.route("/api/logs")
    def api_logs():
        log_file = SERVER_DIR / "logs" / "max_server.log"
        lines = []
        try:
            if log_file.exists():
                with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                    all_lines = f.readlines()
                    lines = [l.rstrip() for l in all_lines[-100:]]
            else:
                lines = ["[System] Log file will be created when the server daemon starts."]
        except Exception as e:
            lines = [f"Error reading logs: {e}"]
        return jsonify({"lines": lines})

    @app.route("/api/health")
    def api_health():
        return jsonify({
            "status": "healthy",
            "uptime": server_state.uptime if server_state else "unknown",
            "timestamp": datetime.utcnow().isoformat()
        })

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8091, debug=True)
