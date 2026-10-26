#!/data/data/com.termux/files/usr/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
#  M.A.X Vivo91 Phone Server — Termux Setup Script
# ══════════════════════════════════════════════════════════════════════════════
#  This script sets up everything needed to run MAX 24/7 on your Vivo 91.
#  Run this ONCE after installing Termux from F-Droid.
#
#  Usage:
#    1. Install Termux from F-Droid (NOT Play Store)
#    2. Open Termux and run:
#       curl -o setup.sh https://raw.githubusercontent.com/<your-repo>/server/termux_setup.sh
#       bash setup.sh
#    OR copy this file to your phone and run it in Termux.
# ══════════════════════════════════════════════════════════════════════════════

set -e

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  M.A.X — Vivo91 Phone Server Setup                     ║"
echo "║  Setting up 24/7 AI Agent Environment in Termux         ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# ── Step 1: Update & Install Base Packages ──
echo "▸ [1/8] Updating Termux packages..."
pkg update -y && pkg upgrade -y

echo "▸ [2/8] Installing core system packages..."
pkg install -y python git wget curl openssh termux-api termux-services

echo "▸ [3/8] Installing build dependencies..."
pkg install -y build-essential libffi openssl libjpeg-turbo libpng libxml2 libxslt freetype

# ── Step 2: Install Python packages ──
echo "▸ [4/8] Upgrading pip..."
pip install --upgrade pip setuptools wheel

echo "▸ [5/8] Installing MAX server dependencies..."
pip install openai requests google-genai google-generativeai
pip install duckduckgo-search beautifulsoup4
pip install python-pptx reportlab
pip install psutil Pillow numpy
pip install python-telegram-bot
pip install flask

echo "  ✅ Python packages installed"

# ── Step 3: Clone or Setup MAX Project ──
echo "▸ [6/8] Setting up MAX project directory..."
MAX_DIR="$HOME/MAX"
if [ -d "$MAX_DIR" ]; then
    echo "  ℹ️  MAX directory already exists at $MAX_DIR"
    echo "  Pull latest changes? (y/n)"
    read -r answer
    if [ "$answer" = "y" ]; then
        cd "$MAX_DIR" && git pull
    fi
else
    echo "  Enter your GitHub repo URL (or press Enter to skip clone):"
    read -r REPO_URL
    if [ -n "$REPO_URL" ]; then
        git clone "$REPO_URL" "$MAX_DIR"
    else
        mkdir -p "$MAX_DIR"
        echo "  ⚠️  Empty directory created. Copy your MAX project files manually."
    fi
fi

# ── Step 4: Setup API Keys Configuration ──
echo "▸ [7/8] Configuring API keys..."
CONFIG_DIR="$MAX_DIR/config"
mkdir -p "$CONFIG_DIR"
KEY_FILE="$CONFIG_DIR/api_keys.json"

if [ ! -f "$KEY_FILE" ]; then
    echo ""
    echo "  🔑 Let's configure your API keys:"
    echo ""

    echo "  Enter Gemini API Key (or press Enter to skip):"
    read -r GEMINI_KEY
    GEMINI_KEY=${GEMINI_KEY:-"YOUR_GEMINI_API_KEY_HERE"}

    echo "  Enter OpenRouter API Key (or press Enter to skip):"
    read -r OPENROUTER_KEY
    OPENROUTER_KEY=${OPENROUTER_KEY:-"YOUR_OPENROUTER_API_KEY_HERE"}

    echo "  Enter Telegram Bot Token (or press Enter to skip):"
    read -r TELEGRAM_TOKEN
    TELEGRAM_TOKEN=${TELEGRAM_TOKEN:-"YOUR_TELEGRAM_BOT_TOKEN_HERE"}

    echo "  Enter your Telegram User ID (for authorization, or press Enter to skip):"
    read -r TELEGRAM_USER_ID

    cat > "$KEY_FILE" << JSONEOF
{
    "gemini_api_key": "$GEMINI_KEY",
    "openrouter_api_key": "$OPENROUTER_KEY",
    "os_system": "android",
    "use_omniroute": false,
    "telegram_bot_token": "$TELEGRAM_TOKEN",
    "telegram_allowed_users": [$TELEGRAM_USER_ID]
}
JSONEOF

    echo "  ✅ API keys saved to $KEY_FILE"
else
    echo "  ℹ️  api_keys.json already exists"
fi

# ── Step 5: Setup Termux Boot & Wake Lock ──
echo "▸ [8/8] Setting up auto-start and wake lock..."

# Install Termux:Boot if not present
pkg install -y termux-services 2>/dev/null || true

# Create boot script directory
BOOT_DIR="$HOME/.termux/boot"
mkdir -p "$BOOT_DIR"

# Auto-start script
cat > "$BOOT_DIR/start-max-server" << 'BOOTEOF'
#!/data/data/com.termux/files/usr/bin/bash
# M.A.X Auto-Start on Boot

# Acquire wake lock to prevent sleep
termux-wake-lock

# Start MAX server
cd $HOME/MAX
export MAX_DEVICE_NAME="Vivo91-Server"
export MAX_DASHBOARD_PORT=8091
nohup python -m server.max_server >> $HOME/MAX/server/logs/max_server.log 2>&1 &

echo "M.A.X Server started in background (PID: $!)"
BOOTEOF

chmod +x "$BOOT_DIR/start-max-server"

# ── Create convenience launcher script ──
cat > "$MAX_DIR/start_server.sh" << 'LAUNCHEOF'
#!/data/data/com.termux/files/usr/bin/bash
# ══════════════════════════════════════════════════════════════
#  M.A.X Server Launcher — Run this to start the server
# ══════════════════════════════════════════════════════════════

cd "$(dirname "$0")"

# Acquire wake lock
termux-wake-lock 2>/dev/null || true

# Set environment
export MAX_DEVICE_NAME="Vivo91-Server"
export MAX_DASHBOARD_PORT=8091
export MAX_HEADLESS=1

echo ""
echo "  🚀 Starting M.A.X Server..."
echo "  📱 Device: $MAX_DEVICE_NAME"
echo "  🌐 Dashboard: http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo 'localhost'):$MAX_DASHBOARD_PORT"
echo ""

python -m server.max_server
LAUNCHEOF

chmod +x "$MAX_DIR/start_server.sh"

# ── Create stop script ──
cat > "$MAX_DIR/stop_server.sh" << 'STOPEOF'
#!/data/data/com.termux/files/usr/bin/bash
echo "Stopping M.A.X Server..."
pkill -f "server.max_server" 2>/dev/null
termux-wake-unlock 2>/dev/null || true
echo "Server stopped."
STOPEOF

chmod +x "$MAX_DIR/stop_server.sh"

# ── Create status check script ──
cat > "$MAX_DIR/server_status.sh" << 'STATUSEOF'
#!/data/data/com.termux/files/usr/bin/bash
echo "═══════════════════════════════════════"
echo "  M.A.X Server Status"
echo "═══════════════════════════════════════"

if pgrep -f "server.max_server" > /dev/null; then
    PID=$(pgrep -f "server.max_server" | head -1)
    echo "  Status:  ✅ RUNNING (PID: $PID)"
    echo "  Uptime:  $(ps -p $PID -o etime= 2>/dev/null || echo 'unknown')"
else
    echo "  Status:  ❌ STOPPED"
fi

# Check dashboard
if curl -s http://localhost:8091/api/health > /dev/null 2>&1; then
    echo "  Dashboard: ✅ ONLINE (http://localhost:8091)"
else
    echo "  Dashboard: ❌ OFFLINE"
fi

# Battery
BATT=$(termux-battery-status 2>/dev/null)
if [ -n "$BATT" ]; then
    PERCENT=$(echo "$BATT" | python -c "import sys,json; print(json.load(sys.stdin).get('percentage','?'))" 2>/dev/null)
    PLUGGED=$(echo "$BATT" | python -c "import sys,json; print(json.load(sys.stdin).get('plugged','?'))" 2>/dev/null)
    echo "  Battery:   🔋 ${PERCENT}% (${PLUGGED})"
fi

# IP
IP=$(hostname -I 2>/dev/null | awk '{print $1}')
echo "  Local IP:  ${IP:-unknown}"
echo "═══════════════════════════════════════"
STATUSEOF

chmod +x "$MAX_DIR/server_status.sh"

# ── Termux notification channel ──
mkdir -p "$HOME/.termux"
echo "extra-keys = [['ESC','/','-','HOME','UP','END','PGUP'],['TAB','CTRL','ALT','LEFT','DOWN','RIGHT','PGDN']]" >> "$HOME/.termux/termux.properties" 2>/dev/null

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  ✅ M.A.X PHONE SERVER SETUP COMPLETE!"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "  📂 Project:    $MAX_DIR"
echo "  🔑 API Keys:   $KEY_FILE"
echo "  📋 Logs:       $MAX_DIR/server/logs/"
echo ""
echo "  ── COMMANDS ──────────────────────────────────────────"
echo "  Start server:  bash $MAX_DIR/start_server.sh"
echo "  Stop server:   bash $MAX_DIR/stop_server.sh"
echo "  Check status:  bash $MAX_DIR/server_status.sh"
echo "  View logs:     tail -f $MAX_DIR/server/logs/max_server.log"
echo ""
echo "  ── IMPORTANT ─────────────────────────────────────────"
echo "  1. Install 'Termux:Boot' from F-Droid for auto-start"
echo "  2. Disable battery optimization for Termux in Settings"
echo "  3. Keep the phone plugged in 24/7"
echo "  4. Access dashboard from any browser on same WiFi:"
echo "     http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo '<your-phone-ip>'):8091"
echo ""
echo "═══════════════════════════════════════════════════════════"
