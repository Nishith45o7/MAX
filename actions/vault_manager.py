"""
actions/vault_manager.py
Encrypted local credential vault — inspired by vaultwarden & bitwarden/server.
AES-256 via Fernet, PBKDF2 key derivation, HIBP breach checking.
"""

import base64
import hashlib
import json
import logging
import os
import secrets
import string
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger("vault_manager")
USER_AGENT = "MAX-MARK-I/1.0"
TIMEOUT = 4.0


def _vault_dir() -> Path:
    d = Path(__file__).resolve().parent.parent / "memory"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _get_fernet():
    """Get or create Fernet cipher using locally stored key."""
    try:
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.primitives import hashes
    except ImportError:
        return None, "cryptography not installed. Run: pip install cryptography"

    key_file = _vault_dir() / ".vault_key"
    salt_file = _vault_dir() / ".vault_salt"

    if not key_file.exists():
        master = Fernet.generate_key()
        key_file.write_bytes(master)
        salt_file.write_bytes(os.urandom(16))

    master_key = key_file.read_bytes()
    salt = salt_file.read_bytes() if salt_file.exists() else b"max_vault_salt_v1"

    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=480000)
    derived = base64.urlsafe_b64encode(kdf.derive(master_key))
    return Fernet(derived), None


def _load_vault() -> list:
    vault_file = _vault_dir() / "vault.enc"
    if not vault_file.exists():
        return []
    fernet, err = _get_fernet()
    if err:
        return []
    try:
        encrypted = vault_file.read_bytes()
        decrypted = fernet.decrypt(encrypted)
        return json.loads(decrypted.decode("utf-8"))
    except Exception as e:
        logger.error(f"Vault decrypt failed: {e}")
        return []


def _save_vault(entries: list) -> str:
    fernet, err = _get_fernet()
    if err:
        return err
    try:
        data = json.dumps(entries, indent=2, ensure_ascii=False).encode("utf-8")
        encrypted = fernet.encrypt(data)
        vault_file = _vault_dir() / "vault.enc"
        vault_file.write_bytes(encrypted)
        return ""
    except Exception as e:
        return f"Save failed: {e}"


def vault_manager(parameters: dict, player=None) -> str:
    """Encrypted credential vault manager."""
    action = (parameters.get("action") or "list").strip().lower()
    aliases = {
        "generate": "generate_password", "gen_password": "generate_password", "gen": "generate_password",
        "breach": "check_breach", "breach_check": "check_breach", "hibp": "check_breach",
        "get": "retrieve", "find": "retrieve", "search": "retrieve",
        "save": "store", "add": "store", "remove": "delete"
    }
    action = aliases.get(action, action)

    fernet, err = _get_fernet()
    if err:
        return f"⚠️ {err}"

    if action == "store":
        service = (parameters.get("service") or parameters.get("service_name", "")).strip()
        username = (parameters.get("username") or "").strip()
        password = (parameters.get("password") or "").strip()
        url = (parameters.get("url") or "").strip()
        notes = (parameters.get("notes") or "").strip()
        if not service:
            return "Service name is required."
        if not password:
            pwd_len = int(parameters.get("password_length", 20))
            password = _generate_password(pwd_len, True, True, True)
        entries = _load_vault()
        for entry in entries:
            if entry["service"].lower() == service.lower():
                entry["username"] = username or entry["username"]
                entry["password"] = password
                entry["url"] = url or entry.get("url", "")
                entry["notes"] = notes or entry.get("notes", "")
                entry["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                save_err = _save_vault(entries)
                if save_err:
                    return f"❌ {save_err}"
                return f"🔐 Updated credentials for '{service}'."
        entries.append({
            "id": len(entries) + 1,
            "service": service,
            "username": username,
            "password": password,
            "url": url,
            "notes": notes,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        })
        save_err = _save_vault(entries)
        if save_err:
            return f"❌ {save_err}"
        return f"🔐 Stored credentials for '{service}' (password: {'generated' if not parameters.get('password') else 'provided'})."

    elif action == "retrieve":
        service = (parameters.get("service") or parameters.get("query", "")).strip().lower()
        if not service:
            return "Service name or query is required."
        entries = _load_vault()
        for entry in entries:
            if service in entry["service"].lower():
                return (
                    f"🔑 Credentials for '{entry['service']}':\n"
                    f"• Username: {entry['username']}\n"
                    f"• Password: {entry['password']}\n"
                    f"• URL: {entry.get('url', 'N/A')}\n"
                    f"• Notes: {entry.get('notes', 'N/A')}\n"
                    f"• Updated: {entry.get('updated_at', 'N/A')}"
                )
        return f"No credentials found for '{service}'."

    elif action == "list":
        entries = _load_vault()
        if not entries:
            return "🔐 Vault is empty. Use action 'store' to add credentials."
        lines = [f"🔐 Vault ({len(entries)} entries):\n"]
        for e in entries:
            masked = e["password"][:2] + "•" * (len(e["password"]) - 2) if len(e["password"]) > 2 else "••••"
            lines.append(f"  #{e.get('id', '?')} {e['service']} — {e['username']} [{masked}]")
        return "\n".join(lines)

    elif action == "delete":
        service = (parameters.get("service") or "").strip().lower()
        entry_id = parameters.get("id")
        entries = _load_vault()
        if entry_id:
            entries = [e for e in entries if e.get("id") != int(entry_id)]
        elif service:
            entries = [e for e in entries if service not in e["service"].lower()]
        else:
            return "Provide 'service' or 'id' to delete."
        _save_vault(entries)
        return f"🗑️ Credential deleted from vault."

    elif action == "generate_password":
        length = int(parameters.get("length", 20))
        use_symbols = parameters.get("symbols", True)
        use_numbers = parameters.get("numbers", True)
        use_upper = parameters.get("uppercase", True)
        pwd = _generate_password(length, use_symbols, use_numbers, use_upper)
        strength = _password_strength(pwd)
        return f"🔑 Generated Password: {pwd}\n• Length: {len(pwd)}\n• Strength: {strength}"

    elif action == "check_breach":
        password = (parameters.get("password") or "").strip()
        if not password:
            return "Password is required for breach check."
        return _check_hibp(password)

    elif action == "export":
        entries = _load_vault()
        if not entries:
            return "Vault is empty."
        desktop = Path.home() / "Desktop"
        if not desktop.exists():
            desktop = Path.home() / "OneDrive" / "Desktop"
        export_data = json.dumps(entries, indent=2, ensure_ascii=False)
        enc = fernet.encrypt(export_data.encode("utf-8"))
        out = desktop / f"vault_backup_{time.strftime('%Y%m%d')}.enc"
        out.write_bytes(enc)
        return f"✅ Encrypted vault backup saved → {out} ({len(entries)} entries)"

    else:
        return f"Unknown action '{action}'. Available: store, retrieve, list, delete, generate_password, check_breach, export"


def _generate_password(length: int = 20, symbols: bool = True,
                       numbers: bool = True, uppercase: bool = True) -> str:
    chars = string.ascii_lowercase
    if uppercase:
        chars += string.ascii_uppercase
    if numbers:
        chars += string.digits
    if symbols:
        chars += "!@#$%^&*()-_=+[]{}|;:,.<>?"
    pwd = [secrets.choice(chars) for _ in range(length)]
    if uppercase:
        pwd[0] = secrets.choice(string.ascii_uppercase)
    if numbers:
        pwd[1] = secrets.choice(string.digits)
    if symbols:
        pwd[2] = secrets.choice("!@#$%^&*()-_=+")
    secrets.SystemRandom().shuffle(pwd)
    return "".join(pwd)


def _password_strength(pwd: str) -> str:
    score = 0
    if len(pwd) >= 12:
        score += 1
    if len(pwd) >= 20:
        score += 1
    if any(c.isupper() for c in pwd):
        score += 1
    if any(c.isdigit() for c in pwd):
        score += 1
    if any(c in string.punctuation for c in pwd):
        score += 1
    return ["Very Weak", "Weak", "Fair", "Strong", "Very Strong", "Excellent"][min(score, 5)]


def _check_hibp(password: str) -> str:
    """Check password against Have I Been Pwned using k-Anonymity."""
    import requests
    sha1 = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
    prefix, suffix = sha1[:5], sha1[5:]
    try:
        resp = requests.get(f"https://api.pwnedpasswords.com/range/{prefix}",
                            timeout=TIMEOUT, headers={"User-Agent": USER_AGENT})
        if resp.status_code == 200:
            for line in resp.text.splitlines():
                parts = line.strip().split(":")
                if parts[0] == suffix:
                    count = int(parts[1])
                    return f"⚠️ BREACHED! This password appeared in {count:,} data breaches. Change it immediately!"
            return "✅ This password has NOT been found in any known data breaches."
        return f"HIBP API returned status {resp.status_code}."
    except Exception as e:
        return f"Breach check failed: {e}"


if __name__ == "__main__":
    print(vault_manager({"action": "generate_password", "length": "24"}))
    print(vault_manager({"action": "check_breach", "password": "password123"}))

