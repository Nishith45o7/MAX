# 🤝 Contributing to MAX

First off — **thank you** for considering contributing to MAX! Every contribution makes this project stronger, and you're helping build the future of autonomous desktop AI.

---

## 📋 Table of Contents

- [🧭 How It Works](#-how-it-works)
- [🐛 Reporting Bugs](#-reporting-bugs)
- [💡 Suggesting Features](#-suggesting-features)
- [🔧 Setting Up for Development](#-setting-up-for-development)
- [📝 Making Changes](#-making-changes)
- [📬 Submitting a Pull Request](#-submitting-a-pull-request)
- [🎨 Code Style Guide](#-code-style-guide)
- [📁 Project Structure Overview](#-project-structure-overview)
- [⚡ Quick Contribution Ideas](#-quick-contribution-ideas)

---

## 🧭 How It Works

MAX uses a **fork-and-pull** contribution model:

```
1. 🍴 Fork the repository
2. 🌿 Create a feature branch
3. 💻 Make your changes
4. ✅ Test everything locally
5. 📬 Submit a Pull Request
6. 👀 Wait for review & approval from the maintainer
7. 🎉 Your contribution gets merged!
```

> **All contributions require approval** from the project maintainer ([@Nishith45o7](https://github.com/Nishith45o7)) before being merged.

---

## 🐛 Reporting Bugs

Found a bug? Help us squash it!

1. **Search existing issues** to avoid duplicates
2. **Open a new issue** using the **Bug Report** template
3. Include:
   - 🖥️ Your OS (Windows/macOS/Linux)
   - 🐍 Python version
   - 📋 Steps to reproduce
   - ✅ Expected behavior
   - ❌ Actual behavior
   - 📸 Screenshots if applicable

---

## 💡 Suggesting Features

Have an idea to make MAX better?

1. **Open a new issue** using the **Feature Request** template
2. Describe:
   - 🎯 The problem you're trying to solve
   - 💡 Your proposed solution
   - 🔄 Any alternatives you've considered

---

## 🔧 Setting Up for Development

```bash
# 1. Fork the repo on GitHub (click the Fork button)

# 2. Clone your fork
git clone https://github.com/YOUR_USERNAME/MAX.git
cd MAX

# 3. Add the original repo as upstream
git remote add upstream https://github.com/Nishith45o7/MAX.git

# 4. Install dependencies
pip install -r requirements.txt
playwright install

# 5. Set up your API keys
cp config/api_keys.example.json config/api_keys.json
# Edit config/api_keys.json with your keys

# 6. Create a feature branch
git checkout -b feature/your-feature-name

# 7. Start developing!
python main.py
```

---

## 📝 Making Changes

### Do's ✅

- Keep changes focused — one feature/fix per PR
- Follow the existing code style
- Add comments for complex logic
- Test your changes on your local machine
- Update documentation if needed

### Don'ts ❌

- Don't change multiple unrelated things in one PR
- Don't commit API keys or personal data
- Don't modify `.gitignore` without reason
- Don't break existing functionality
- Don't add heavy dependencies without discussion

---

## 📬 Submitting a Pull Request

1. **Sync with upstream** before submitting:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Push your branch**:
   ```bash
   git push origin feature/your-feature-name
   ```

3. **Open a Pull Request** on GitHub:
   - Use a clear, descriptive title
   - Fill out the PR template
   - Reference any related issues
   - Add screenshots for UI changes

4. **Wait for review** — the maintainer will review and may request changes.

---

## 🎨 Code Style Guide

| Rule | Details |
|:---|:---|
| **Language** | Python 3.11+ |
| **Indentation** | 4 spaces (no tabs) |
| **Line Length** | Max 100 characters |
| **Naming** | `snake_case` for functions/variables, `PascalCase` for classes |
| **Imports** | Group: stdlib → third-party → local, with blank lines between |
| **Docstrings** | Required for public functions and classes |
| **Comments** | Explain *why*, not *what* |
| **Type Hints** | Encouraged for function signatures |

---

## 📁 Project Structure Overview

If you're wondering where to add your contribution:

| Directory | What Goes Here |
|:---|:---|
| `actions/` | New tool/action modules (e.g., new integrations) |
| `agent/` | Task planning and execution logic |
| `gateway/` | External communication channels |
| `memory/` | Memory and context management |
| `core/` | Core system prompts and config |
| `config/` | Configuration templates |
| Root files | Core engine (main.py, max_brain.py, ui.py) |

### Adding a New Action Module

1. Create a new file in `actions/` (e.g., `actions/my_feature.py`)
2. Define a function that accepts parameters and returns a string result
3. Register it in `max_brain.py` as a new tool
4. Add the tool description to `core/prompt.txt`
5. Test via voice or text input

---

## ⚡ Quick Contribution Ideas

Not sure where to start? Here are some beginner-friendly ideas:

- 🐛 Fix typos in documentation
- 📝 Improve code comments and docstrings
- 🌐 Add support for a new language in responses
- 🔌 Create a new action module (e.g., Spotify control, email reader)
- 🎨 UI improvements and new themes
- 🧪 Add error handling to existing modules
- 📱 Enhance Telegram gateway features
- 🖥️ Improve cross-platform compatibility (Linux/macOS fixes)

---

## 🙏 Thank You

Every contribution, no matter how small, is valued. Whether it's fixing a typo, adding a feature, or reporting a bug — **you're making MAX better for everyone**.

---

<p align="center">
  <sub>By contributing, you agree that your contributions will be licensed under the same <a href="https://creativecommons.org/licenses/by-nc/4.0/">CC BY-NC 4.0</a> license as the project.</sub>
</p>
