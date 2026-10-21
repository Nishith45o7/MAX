# Security Policy

## 🔐 Reporting a Vulnerability

If you discover a security vulnerability in MAX, please report it responsibly.

**DO NOT** open a public issue for security vulnerabilities.

Instead, please:

1. **Open a private security advisory** via GitHub's [Security Advisories](https://github.com/Nishith45o7/MAX/security/advisories/new)
2. Or **contact the maintainer directly** via GitHub

### What to include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

## 🛡️ Security Best Practices for Users

- **Never commit** your `config/api_keys.json` to a public repository
- **Keep your API keys** private — use the `.gitignore` (already configured)
- **Whitelist Telegram IDs** if using the Telegram gateway
- **Keep dependencies updated** via `pip install -r requirements.txt --upgrade`

## ✅ Supported Versions

| Version | Supported |
|:---|:---:|
| Latest `main` branch | ✅ |
| Older commits | ❌ |
