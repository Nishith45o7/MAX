<p align="center">
  <img src="assets/max_banner.jpg" alt="MAX — Autonomous AI Desktop Assistant" width="100%"/>
</p>

<h1 align="center">
  <br>
  M . A . X
  <br>
</h1>

<h3 align="center">
  <em>Modular Autonomous eXecutor — Your Personal JARVIS-Style AI</em>
</h3>

<p align="center">
  <a href="#-quick-start"><img src="https://img.shields.io/badge/⚡_Quick_Start-000000?style=for-the-badge&logoColor=white" alt="Quick Start"/></a>
  <a href="#-features"><img src="https://img.shields.io/badge/✨_Features-000000?style=for-the-badge&logoColor=white" alt="Features"/></a>
  <a href="#-architecture"><img src="https://img.shields.io/badge/🏛️_Architecture-000000?style=for-the-badge&logoColor=white" alt="Architecture"/></a>
  <a href="#-demo"><img src="https://img.shields.io/badge/🎬_Demo-000000?style=for-the-badge&logoColor=white" alt="Demo"/></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11%20%7C%203.12-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/Gemini_Live-Native_Audio-4285F4?style=flat-square&logo=google&logoColor=white" alt="Gemini"/>
  <img src="https://img.shields.io/badge/OpenRouter-Free_Tier-6366F1?style=flat-square&logo=openai&logoColor=white" alt="OpenRouter"/>
  <img src="https://img.shields.io/badge/Platform-Win%20%7C%20Mac%20%7C%20Linux-0078D6?style=flat-square&logo=windows&logoColor=white" alt="Platform"/>
  <img src="https://img.shields.io/badge/License-CC%20BY--NC%204.0-EF9421?style=flat-square&logo=creativecommons&logoColor=white" alt="License"/>
  <img src="https://img.shields.io/github/stars/Nishith45o7/MAX?style=flat-square&color=FFD700&logo=github" alt="Stars"/>
  <img src="https://img.shields.io/github/forks/Nishith45o7/MAX?style=flat-square&color=00D4AA&logo=github" alt="Forks"/>
</p>

<br>

<p align="center">
  <strong>A real-time voice AI that can hear, see, understand, and control your computer.</strong>
  <br>
  <sub>Local execution • Zero subscriptions • Cross-platform • Total autonomy</sub>
</p>

---

<br>

## 🎬 Demo

<p align="center">
  <a href="https://youtu.be/ldvDNzwnM8k">
    <img src="https://img.shields.io/badge/▶️_Watch_Full_Demo_on_YouTube-FF0000?style=for-the-badge&logo=youtube&logoColor=white" alt="YouTube Demo"/>
  </a>
</p>

<br>

---

## 🧬 What is MAX?

**MAX** (Modular Autonomous eXecutor) is an open-source, **JARVIS-inspired desktop AI** that transforms your computer into an intelligent, voice-controlled system. It doesn't just answer questions — it **sees your screen**, **hears your voice**, **remembers your preferences**, and **takes action** on your behalf.

Built on **Gemini Live** for real-time native audio and **OpenRouter** for cost-free LLM routing, MAX operates with **zero monthly subscriptions** while delivering capabilities that rival commercial AI assistants.

> 💡 *Think of it as the bridge between human intent and operating system execution.*

<br>

---

## ✨ Features

<table>
<tr>
<td width="50%">

### 🎙️ Real-Time Voice Engine
Ultra-low latency conversation powered by **Gemini Live native audio**. Speak naturally in **any language** — MAX responds instantly with human-like voice.

### 👁️ Visual Intelligence
Real-time **screen capture & analysis**, **webcam vision**, and **document processing**. MAX sees what you see and understands context instantly.

### 🧠 Persistent Memory
An intelligent memory system that **learns your identity, preferences, projects, and relationships** across sessions — creating a truly personalized experience.

### 🖥️ Full OS Control
Launch apps, manage files, control volume/brightness, take screenshots, manage windows — all through **natural voice commands** or **text**.

</td>
<td width="50%">

### 🌐 Web & Browser Automation
Autonomous **web search**, **browser control** via Playwright, and intelligent information extraction — all without lifting a finger.

### 🎮 Gaming Integration
Direct **Steam & Epic Games** management — install, update, list, and monitor your game library through voice commands.

### ✈️ Smart Actions
**Flight search**, **weather reports**, **reminders**, **YouTube operations**, **Telegram gateway**, and **document generation** (PDF & PPTX).

### 🤖 Autonomous Agent
A built-in **planning & execution engine** that breaks complex multi-step goals into actionable tasks and executes them sequentially.

</td>
</tr>
</table>

<br>

---

## 🏛️ Architecture

```
╔══════════════════════════════════════════════════════════════════════╗
║                         M . A . X   —   CORE                       ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║   ┌──────────────┐    ┌──────────────────┐    ┌────────────────┐    ║
║   │  🎙️ VOICE    │───▶│  🧠 MAX BRAIN    │◀──▶│  💾 MEMORY     │    ║
║   │  Gemini Live │    │  (Unified Engine) │    │  SQLite + JSON │    ║
║   │  Native Audio│    │  Function Calling │    │  Semantic Ctx  │    ║
║   └──────────────┘    └────────┬─────────┘    └────────────────┘    ║
║                                │                                     ║
║          ┌─────────────────────┼─────────────────────┐              ║
║          ▼                     ▼                     ▼              ║
║   ┌─────────────┐    ┌─────────────────┐    ┌──────────────┐       ║
║   │ 🔧 ACTIONS  │    │ 🌐 GATEWAY      │    │ 🖥️ UI (HUD)  │       ║
║   │             │    │                 │    │              │       ║
║   │ • Desktop   │    │ • OmniRoute     │    │ • PyQt6      │       ║
║   │ • Browser   │    │ • Telegram Bot  │    │ • Dark/Light │       ║
║   │ • Files     │    │ • OpenRouter    │    │ • Drag & Drop│       ║
║   │ • Games     │    │                 │    │ • Responsive │       ║
║   │ • Web Search│    └─────────────────┘    └──────────────┘       ║
║   │ • Screen    │                                                   ║
║   │ • Code      │                                                   ║
║   │ • Flights   │                                                   ║
║   │ • YouTube   │                                                   ║
║   │ • Weather   │                                                   ║
║   │ • Reminders │                                                   ║
║   │ • Documents │                                                   ║
║   └─────────────┘                                                   ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
```

<br>

---

## 📁 Project Structure

```
MAX/
├── 🧠 main.py                  # Voice engine — Gemini Live real-time audio
├── 🤖 max_brain.py             # Central brain — unified function-calling engine
├── 🖥️ ui.py                    # PyQt6 HUD — adaptive dark/light interface
├── 🔧 or_client.py             # OpenRouter API client
├── 📄 doc_tools.py             # PDF & PowerPoint generation
├── 🌐 web_tool.py              # Web search utility
│
├── actions/                     # 🔌 Modular action plugins
│   ├── browser_control.py       #    Playwright-powered browser automation
│   ├── code_helper.py           #    Intelligent code analysis & generation
│   ├── computer_control.py      #    Terminal & system command execution
│   ├── computer_settings.py     #    Volume, brightness, shortcuts, windows
│   ├── desktop.py               #    Desktop automation (clicks, typing)
│   ├── dev_agent.py             #    Full development workflow agent
│   ├── file_controller.py       #    File CRUD operations
│   ├── file_processor.py        #    Document upload & analysis
│   ├── flight_finder.py         #    Flight search & comparison
│   ├── game_updater.py          #    Steam & Epic Games management
│   ├── open_app.py              #    Cross-platform app launcher
│   ├── public_api_tools.py      #    Public API integrations
│   ├── reminder.py              #    Smart reminders
│   ├── screen_processor.py      #    Real-time screen vision (Gemini)
│   ├── send_message.py          #    Message dispatch system
│   ├── weather_report.py        #    Weather information
│   ├── web_search.py            #    DuckDuckGo search engine
│   └── youtube_video.py         #    YouTube operations
│
├── agent/                       # 🤖 Autonomous task engine
│   ├── planner.py               #    Multi-step goal decomposition
│   ├── executor.py              #    Sequential task execution
│   ├── task_queue.py            #    Priority task queue
│   └── error_handler.py        #    Self-healing error recovery
│
├── gateway/                     # 🌐 External communication layer
│   ├── omniroute_manager.py     #    OmniRoute LLM gateway
│   └── telegram_gateway.py      #    Telegram bot remote control
│
├── memory/                      # 💾 Persistent intelligence
│   ├── memory_manager.py        #    Identity & preference memory
│   ├── db.py                    #    SQLite conversation store
│   └── config_manager.py        #    Configuration persistence
│
├── core/                        # ⚙️ Core system
│   └── prompt.txt               #    System personality & rules
│
├── config/                      # 🔑 Configuration
│   └── api_keys.example.json    #    API key template
│
├── requirements.txt             # 📦 Python dependencies
├── setup.py                     # 🚀 One-click installer
├── run_max.bat                  # ▶️ Windows launcher
└── start_omniroute.bat          # 🔀 OmniRoute server launcher
```

<br>

---

## ⚡ Quick Start

### Prerequisites

| Requirement | Details |
|:---:|:---|
| **OS** | Windows 10/11 • macOS • Linux |
| **Python** | 3.11 or 3.12 |
| **Microphone** | Required for voice interaction |
| **API Keys** | [Free Gemini API Key](https://aistudio.google.com/apikey) + [Free OpenRouter API Key](https://openrouter.ai/keys) |

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/Nishith45o7/MAX.git
cd MAX

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install Playwright browsers (for web automation)
playwright install

# 4. Configure your API keys
#    Copy the template and add your keys:
cp config/api_keys.example.json config/api_keys.json
#    Then edit config/api_keys.json with your actual API keys

# 5. Launch MAX
python main.py
```

> [!NOTE]
> **Windows users** can simply double-click `run_max.bat` to launch MAX after configuration.

> [!TIP]
> Some OS-specific dependencies may not be bundled. If you hit a `ModuleNotFoundError`, install the missing package: `pip install <module_name>`

<br>

---

## 🔑 Configuration

Create `config/api_keys.json` from the template:

```json
{
    "gemini_api_key": "YOUR_GEMINI_API_KEY_HERE",
    "openrouter_api_key": "YOUR_OPENROUTER_API_KEY_HERE",
    "os_system": "windows",
    "use_omniroute": true,
    "omniroute_base_url": "http://localhost:20128/v1",
    "omniroute_api_key": "omniroute",
    "omniroute_model": "auto"
}
```

| Key | Where to Get It | Cost |
|:---|:---|:---:|
| `gemini_api_key` | [Google AI Studio](https://aistudio.google.com/apikey) | **Free** |
| `openrouter_api_key` | [OpenRouter](https://openrouter.ai/keys) | **Free** |

<br>

---

## 🎯 What Can MAX Do?

<details>
<summary><b>🎙️ Voice Commands</b> — Talk naturally, get instant action</summary>
<br>

```
"Hey Max, open Chrome and search for Python tutorials"
"What's on my screen right now?"
"Set my volume to 50 percent"
"Take a screenshot and save it to desktop"
"What's the weather in Tokyo?"
```

</details>

<details>
<summary><b>🖥️ System Control</b> — Full OS automation</summary>
<br>

```
"Open Visual Studio Code"
"Minimize all windows"
"Turn up the brightness"
"Lock my computer"
"Restart the system"
```

</details>

<details>
<summary><b>📂 File Operations</b> — Smart file management</summary>
<br>

```
"Create a new folder called 'Project Alpha' on my desktop"
"Find all PDF files in my downloads"
"Move this file to documents"
"Read this PDF and summarize it"
"Create a presentation about AI trends"
```

</details>

<details>
<summary><b>🌐 Web & Research</b> — Intelligent browsing</summary>
<br>

```
"Search for the latest news about SpaceX"
"Compare iPhone 16 vs Samsung S25"
"Find me flights from Delhi to London next month"
"Open YouTube and play lofi music"
```

</details>

<details>
<summary><b>🎮 Gaming</b> — Steam & Epic management</summary>
<br>

```
"List all my installed Steam games"
"Update Counter-Strike"
"Download GTA V from Epic Games"
"Check my download progress"
```

</details>

<details>
<summary><b>🧠 Memory & Context</b> — MAX remembers everything</summary>
<br>

```
"Remember that my project deadline is December 15th"
"What do you know about me?"
"I prefer dark mode and minimal responses"
"My friend's name is Alex, he's a designer"
```

</details>

<br>

---

## 🔀 OmniRoute Integration

MAX uses **OmniRoute** to intelligently distribute LLM calls across free-tier models, dramatically extending usage limits at zero cost.

```
┌─────────────────┐          ┌──────────────────┐
│   Gemini Live    │ ──────▶  │  Real-time Voice  │
│   (Native Audio) │          │  + Tool Calling   │
└─────────────────┘          └──────────────────┘

┌─────────────────┐          ┌──────────────────┐
│   OpenRouter     │ ──────▶  │  Web Search       │
│   (Free Tier)    │          │  Memory Queries   │
│                  │          │  Desktop Control  │
│                  │          │  Code Generation  │
└─────────────────┘          └──────────────────┘
```

> **Result:** 40% faster interaction speed with virtually unlimited request capacity.

<br>

---

## 📱 Telegram Remote Control

Control MAX remotely from your phone via Telegram:

1. Create a bot with [@BotFather](https://t.me/BotFather)
2. Add the token to your config
3. Whitelist your Telegram user ID
4. Run `start_omniroute.bat` and use the `/start` command

> [!IMPORTANT]
> Only whitelisted user IDs can interact with your MAX instance for security.

<br>

---

## 🛡️ Security

- 🔐 All API keys stored locally in `config/api_keys.json` (git-ignored)
- 🚫 No data sent to third-party servers beyond API calls
- 🏠 Fully local execution — your data stays on your machine
- 🔒 Telegram gateway supports user whitelisting

<br>

---

## 🤝 Contributing

Contributions are welcome! Here's how to get started:

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/amazing-feature`
3. **Commit** your changes: `git commit -m 'Add amazing feature'`
4. **Push** to the branch: `git push origin feature/amazing-feature`
5. **Open** a Pull Request

<br>

---

## ⚠️ License

This project is licensed under **[Creative Commons BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)** — personal and non-commercial use only.

<br>

---

## 👤 Connect

<p align="center">
  <a href="https://www.youtube.com/@FatihMakes">
    <img src="https://img.shields.io/badge/YouTube-@FatihMakes-FF0000?style=for-the-badge&logo=youtube&logoColor=white" alt="YouTube"/>
  </a>
  &nbsp;
  <a href="https://www.instagram.com/fatihmakes">
    <img src="https://img.shields.io/badge/Instagram-@fatihmakes-E4405F?style=for-the-badge&logo=instagram&logoColor=white" alt="Instagram"/>
  </a>
  &nbsp;
  <a href="https://github.com/Nishith45o7/MAX">
    <img src="https://img.shields.io/badge/GitHub-Nishith45o7-181717?style=for-the-badge&logo=github&logoColor=white" alt="GitHub"/>
  </a>
</p>

<br>

---

<p align="center">
  <strong>⭐ Star this repo if MAX impressed you — it fuels the journey to Mark 100!</strong>
</p>

<p align="center">
  <sub>Engineered with ❤️ — building a real-world autonomous AI, one commit at a time.</sub>
</p>
