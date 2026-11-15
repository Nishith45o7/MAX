"""
actions/inbox_agent.py
Smart email triage, clipboard AI, task delegation.
Inspired by agentic-inbox, agency-agents, paperclip, team-skills.
"""
import json, logging, time, imaplib, email as email_lib
from pathlib import Path
from email.header import decode_header
logger = logging.getLogger("inbox_agent")

def _mem(name):
    p = Path(__file__).resolve().parent.parent / "memory" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def _load(name, default=None):
    p = _mem(name)
    if p.exists():
        try: return json.loads(p.read_text("utf-8"))
        except: pass
    return default if default is not None else {}

def _save(name, data):
    _mem(name).write_text(json.dumps(data, indent=2, ensure_ascii=False), "utf-8")

def _decode_header(val):
    if not val: return ""
    parts = decode_header(val)
    return " ".join(p.decode(c or "utf-8") if isinstance(p, bytes) else p for p, c in parts)

def inbox_agent(parameters: dict, player=None) -> str:
    action = (parameters.get("action") or "check_inbox").strip().lower()
    aliases = {
        "check_email": "check_inbox", "send_email": "compose_email", "compose": "compose_email",
        "send": "compose_email", "inbox": "check_inbox", "reply": "smart_reply",
        "clipboard": "clipboard_ai", "history": "clipboard_history",
        "delegate": "delegate_task", "broadcast": "team_broadcast", "status": "task_status"
    }
    action = aliases.get(action, action)

    # ── Email ──
    if action in ("check_inbox", "summarize_inbox"):
        cfg = _load("email_config.json")
        if not cfg.get("imap_server") or not cfg.get("email"):
            return ("📧 Email not configured. Create memory/email_config.json with:\n"
                    '  {"imap_server":"imap.gmail.com","email":"you@gmail.com","password":"app-password","smtp_server":"smtp.gmail.com"}')
        try:
            mail = imaplib.IMAP4_SSL(cfg["imap_server"])
            mail.login(cfg["email"], cfg["password"])
            mail.select("inbox")
            _, nums = mail.search(None, "UNSEEN" if action == "check_inbox" else "ALL")
            ids = nums[0].split()[-10:] if nums[0] else []
            if not ids:
                mail.logout()
                return "📧 No unread emails." if action == "check_inbox" else "📧 Inbox empty."
            lines = [f"📧 {'Unread' if action=='check_inbox' else 'Recent'} Emails ({len(ids)}):\n"]
            for mid in reversed(ids):
                _, data = mail.fetch(mid, "(RFC822)")
                msg = email_lib.message_from_bytes(data[0][1])
                subj = _decode_header(msg["Subject"])[:80]
                frm = _decode_header(msg["From"])[:50]
                lines.append(f"  • {subj}\n    From: {frm}")
            mail.logout()
            return "\n".join(lines)
        except Exception as e:
            return f"Email check failed: {e}"

    elif action == "compose_email":
        to = parameters.get("to", "")
        subject = parameters.get("subject", "")
        body = parameters.get("body", "")
        if not to or not body:
            return "To and body are required."
        draft = f"To: {to}\nSubject: {subject}\n\n{body}"
        out = Path(__file__).resolve().parent.parent / "memory" / f"draft_{int(time.time())}.eml"
        out.write_text(draft, "utf-8")
        return f"📝 Draft saved → {out}"

    elif action == "smart_reply":
        email_text = (parameters.get("email_text") or "").strip()
        if not email_text:
            return "Email text is required."
        try:
            from or_client import client as or_client
            result = or_client.chat(
                f"Generate 3 concise reply options for this email:\n\n{email_text}",
                system="You are a professional email assistant. Generate 3 reply options: formal, friendly, brief."
            )
            return f"💬 Reply Suggestions:\n\n{result}"
        except:
            return ("💬 Reply Suggestions:\n"
                    "1. [Formal] Thank you for your message. I will review and respond shortly.\n"
                    "2. [Friendly] Thanks for reaching out! I'll get back to you soon.\n"
                    "3. [Brief] Noted, will follow up.")

    # ── Clipboard AI ──
    elif action == "clipboard_ai":
        try:
            import pyperclip
            content = pyperclip.paste()
        except:
            content = parameters.get("text", "")
        if not content:
            return "Clipboard is empty."
        operation = (parameters.get("operation") or "summarize").lower()
        hist = _load("clipboard_history.json", [])
        hist.insert(0, {"content": content[:500], "time": time.strftime("%Y-%m-%d %H:%M:%S")})
        _save("clipboard_history.json", hist[:50])
        try:
            from or_client import client as or_client
            ops = {"summarize": "Summarize this text concisely", "translate": "Translate to English",
                   "format": "Reformat this text cleanly", "extract": "Extract key data points"}
            prompt = f"{ops.get(operation, operation)}:\n\n{content[:2000]}"
            result = or_client.chat(prompt)
            return f"📋 Clipboard ({operation}):\n\n{result}"
        except:
            return f"📋 Clipboard content ({len(content)} chars):\n{content[:500]}"

    elif action == "clipboard_history":
        hist = _load("clipboard_history.json", [])
        if not hist:
            return "No clipboard history."
        lines = [f"📋 Clipboard History ({len(hist)} items):\n"]
        for h in hist[:10]:
            lines.append(f"  • [{h['time']}] {h['content'][:60]}...")
        return "\n".join(lines)

    # ── Task Delegation ──
    elif action == "delegate_task":
        title = (parameters.get("title") or "").strip()
        assignee = (parameters.get("assignee") or "unassigned").strip()
        priority = (parameters.get("priority") or "normal").strip()
        desc = (parameters.get("description") or "").strip()
        due = (parameters.get("due_date") or "").strip()
        if not title:
            return "Task title is required."
        tasks = _load("delegated_tasks.json", {"tasks": []})
        tid = len(tasks["tasks"]) + 1
        tasks["tasks"].append({
            "id": tid, "title": title, "description": desc, "assignee": assignee,
            "status": "pending", "priority": priority, "due_date": due,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        _save("delegated_tasks.json", tasks)
        return f"✅ Task #{tid} delegated to {assignee}: {title} [{priority}]"

    elif action == "task_status":
        tasks = _load("delegated_tasks.json", {"tasks": []})
        tlist = tasks.get("tasks", [])
        if not tlist:
            return "No delegated tasks."
        tid = parameters.get("id")
        status = parameters.get("status")
        if tid and status:
            for t in tlist:
                if t["id"] == int(tid):
                    t["status"] = status
                    _save("delegated_tasks.json", tasks)
                    return f"✅ Task #{tid} status → {status}"
            return f"Task #{tid} not found."
        lines = [f"📋 Tasks ({len(tlist)}):\n"]
        for t in tlist[-15:]:
            icon = {"pending": "⏳", "in_progress": "🔄", "done": "✅", "blocked": "🚫"}.get(t["status"], "⚪")
            lines.append(f"  {icon} #{t['id']} {t['title']} → {t['assignee']} [{t['priority']}]")
        return "\n".join(lines)

    elif action == "team_broadcast":
        message = (parameters.get("message") or "").strip()
        if not message:
            return "Message is required."
        tasks = _load("delegated_tasks.json", {"tasks": []})
        assignees = set(t["assignee"] for t in tasks.get("tasks", []) if t["assignee"] != "unassigned")
        return f"📢 Broadcast to {len(assignees)} team members: {message}\n  Recipients: {', '.join(assignees) or 'none (add tasks first)'}"

    else:
        return (f"Unknown action '{action}'. Available: check_inbox, summarize_inbox, compose_email, "
                "smart_reply, clipboard_ai, clipboard_history, delegate_task, task_status, team_broadcast")

if __name__ == "__main__":
    print(inbox_agent({"action": "task_status"}))

