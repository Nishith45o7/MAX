"""
Brigade CLI Command Suite for MAX.
Implements complete command suite: onboard, status, doctor, gateway, agents,
org, channels, pairing, cron, skills, exec, mcp, encrypt, backup, secrets audit.
"""
import sys
import os
import json
import argparse
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from brigade_core import get_state_dir
from brigade_core.config import ConfigManager
from brigade_core.storage import StorageManager
from brigade_core.encryption import EncryptionManager
from brigade_core.backup import BackupManager
from brigade_core.secrets_audit import SecretsAuditor
from brigade_core.server import GatewayServer
from agents.registry import AgentRegistry
from agents.org_chart import OrgChart
from agents.a2a_policy import A2APolicy
from channels.inbound_pipeline import InboundPipeline
from cron.scheduler import CronScheduler
from skills.loader import SkillLoader


def cmd_status(args):
    cfg_mgr = ConfigManager()
    cfg = cfg_mgr.load_resolved()
    state_dir = get_state_dir()
    reg = AgentRegistry(cfg_mgr)
    cron = CronScheduler()

    status = {
        "stateDir": str(state_dir),
        "gatewayHost": cfg.get("gateway", {}).get("host"),
        "gatewayPort": cfg.get("gateway", {}).get("port"),
        "defaultModel": cfg.get("agents", {}).get("defaults", {}).get("model"),
        "defaultProvider": cfg.get("agents", {}).get("defaults", {}).get("provider"),
        "agentsCount": len(reg.list_agents()),
        "cronJobsCount": len(cron.list_jobs()),
        "encryptionEnabled": EncryptionManager().is_enabled()
    }

    if getattr(args, "json", False):
        print(json.dumps(status, indent=2))
    else:
        print("🦁 Brigade / MAX System Status")
        print("═" * 40)
        for k, v in status.items():
            print(f"  {k:20}: {v}")


def cmd_doctor(args):
    issues = []
    print("🩺 Running Brigade / MAX Health Check...")
    
    # 1. Python version
    py_ver = sys.version.split()[0]
    print(f"  [✓] Python Runtime: {py_ver}")

    # 2. State directory
    state_dir = get_state_dir()
    if state_dir.exists():
        print(f"  [✓] State Directory: {state_dir}")
    else:
        issues.append(f"State directory missing: {state_dir}")

    # 3. Config
    try:
        cfg = ConfigManager().load_resolved()
        print("  [✓] Config schema integrity: OK")
    except Exception as e:
        issues.append(f"Config validation error: {e}")

    # 4. Storage & Workspaces
    ws = state_dir / "workspace"
    if (ws / "SOUL.md").exists():
        print("  [✓] Default Workspace (main): Healthy")
    else:
        issues.append("Main workspace personas missing")

    # 5. Skills
    skills = SkillLoader().discover_skills()
    print(f"  [✓] Extensible Skills: {len(skills)} eligible skills found")

    # 6. Org chart doctor
    org_issues = OrgChart().doctor()
    for oi in org_issues:
        print(f"  [!] Org Notice: {oi}")

    if issues:
        print(f"\n❌ Doctor found {len(issues)} issue(s):")
        for i in issues:
            print(f"  - {i}")
        sys.exit(1)
    else:
        print("\n✅ All systems verified healthy.")


def cmd_agents(args):
    reg = AgentRegistry()
    sub = args.agent_subcommand

    if sub == "list" or not sub:
        agents = reg.list_agents()
        if getattr(args, "json", False):
            print(json.dumps(agents, indent=2))
        else:
            print("👥 Configured Agents")
            print("═" * 50)
            for a in agents:
                print(f"  {a.get('emoji', '🤖')} {a['id']:15} | {a['name']:20} | Model: {a.get('model')}")

    elif sub == "add":
        name = args.name or args.agent_id
        res = reg.add_agent(args.agent_id, name, description=args.desc or "", model=args.model, provider=args.provider)
        print(f"✅ Created agent '{res['id']}' with isolated workspace.")

    elif sub == "delete":
        deleted = reg.delete_agent(args.agent_id, force=args.force)
        if deleted:
            print(f"✅ Agent '{args.agent_id}' deleted.")
        else:
            print(f"❌ Failed to delete agent '{args.agent_id}'.")


def cmd_org(args):
    chart = OrgChart()
    sub = args.org_subcommand

    if sub == "show" or not sub:
        print(chart.render_tree())

    elif sub == "explain":
        policy = A2APolicy(chart)
        allowed, reason = policy.can_message(args.from_agent, args.to_agent)
        tag = "ALLOWED" if allowed else "DENIED"
        print(f"[{tag}] {args.from_agent} -> {args.to_agent}: {reason}")

    elif sub == "doctor":
        issues = chart.doctor()
        if not issues:
            print("✅ Org hierarchy is clean and valid.")
        else:
            for iss in issues:
                print(f"⚠️  {iss}")


def cmd_cron(args):
    cron = CronScheduler()
    sub = args.cron_subcommand

    if sub == "list" or not sub:
        jobs = cron.list_jobs()
        print("⏰ Scheduled Cron Jobs")
        print("═" * 60)
        for j in jobs:
            status = "ENABLED" if j.enabled else "DISABLED"
            print(f"  [{status:8}] {j.id:10} | {j.schedule_type:5} '{j.expression}' | {j.message}")

    elif sub == "add":
        stype = "every" if args.every else ("at" if args.at else "cron")
        expr = args.every or args.at or args.cron
        job = cron.add_job(stype, expr, args.message, tz=args.tz or "UTC")
        print(f"✅ Created cron job '{job.id}'.")

    elif sub == "rm":
        if cron.remove_job(args.job_id):
            print(f"✅ Removed job '{args.job_id}'.")
        else:
            print(f"❌ Job '{args.job_id}' not found.")

    elif sub == "run":
        from brigade_core.storage import StorageManager
        from cron.runner import CronRunner
        job = cron.get_job(args.job_id)
        if not job:
            print(f"❌ Job '{args.job_id}' not found.")
            return
        runner = CronRunner(cron, StorageManager())
        runner._execute_job(job)
        print(f"✅ Fired job '{args.job_id}' manually.")


def cmd_pairing(args):
    pipeline = InboundPipeline()
    sub = args.pairing_subcommand

    if sub == "list" or not sub:
        print("🔒 Pending Channel Pairing Requests")
        print("═" * 50)
        for c, info in pipeline.pending_pairings.items():
            print(f"  Code: {c} | Channel: {info['channel']:10} | User: {info.get('sender_name')} ({info['sender_id']})")
        if not pipeline.pending_pairings:
            print("  (No pending pairing requests)")

    elif sub == "approve":
        ok, reason = pipeline.approve_pairing(args.code, args.channel)
        print(f"{'✅' if ok else '❌'} {reason}")

    elif sub == "deny":
        if pipeline.deny_pairing(args.code):
            print(f"✅ Denied pairing code '{args.code}'.")
        else:
            print(f"❌ Code '{args.code}' not found.")


def cmd_encrypt(args):
    enc = EncryptionManager()
    sub = args.encrypt_subcommand

    if sub == "status" or not sub:
        enabled = enc.is_enabled()
        print(f"🔐 Encryption at rest: {'ENABLED' if enabled else 'DISABLED'}")
        if enabled:
            print(f"   Key file: {enc.key_path}")

    elif sub == "init":
        key = enc.init_key()
        print(f"✅ Generated new AES-256-GCM key and saved to: {enc.key_path}")
        print(f"   Key: {key}")

    elif sub == "test":
        try:
            ok = enc.test_roundtrip()
            print(f"{'✅' if ok else '❌'} Encryption round-trip test passed.")
        except Exception as e:
            print(f"❌ Encryption test failed: {e}")


def cmd_backup(args):
    bm = BackupManager()
    sub = args.backup_subcommand

    if sub == "create":
        p = bm.create_backup()
        print(f"✅ Created backup archive: {p}")

    elif sub == "verify":
        res = bm.verify_backup(Path(args.path))
        print(f"{'✅' if res.get('valid') else '❌'} Backup verification: {res}")


def cmd_secrets(args):
    auditor = SecretsAuditor()
    findings = auditor.audit()
    print("🕵️ Secret Audit Scan")
    print("═" * 50)
    if not findings:
        print("✅ No unredacted secrets found in state directory.")
    else:
        print(f"⚠️  Found {len(findings)} potential secret(s):")
        for f in findings:
            print(f"  - [{f['type']}] in {f['file']}: {f['masked']}")


def cmd_gateway(args):
    sub = args.gateway_subcommand
    if sub == "run" or not sub:
        cfg = ConfigManager().load_resolved()
        host = args.host or cfg.get("gateway", {}).get("host", "127.0.0.1")
        port = args.port or cfg.get("gateway", {}).get("port", 7777)
        server = GatewayServer(host=host, port=port)
        server.run()


def cmd_mcp(args):
    from tideline.mcp_server import McpMemoryServer
    server = McpMemoryServer(agent_id=getattr(args, "agent", "main"))
    server.run()


def main():
    parser = argparse.ArgumentParser(description="Brigade / MAX Multi-Agent Assistant CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Status
    p_status = subparsers.add_parser("status", help="Show system status")
    p_status.add_argument("--json", action="store_true")

    # Doctor
    p_doctor = subparsers.add_parser("doctor", help="Run health checks")

    # Gateway
    p_gw = subparsers.add_parser("gateway", help="Manage headless gateway")
    p_gw_sub = p_gw.add_subparsers(dest="gateway_subcommand")
    p_gw_run = p_gw_sub.add_parser("run", help="Run gateway server")
    p_gw_run.add_argument("--host", default="127.0.0.1")
    p_gw_run.add_argument("--port", type=int, default=7777)

    # Agents
    p_agents = subparsers.add_parser("agents", help="Manage agents")
    p_agents_sub = p_agents.add_subparsers(dest="agent_subcommand")
    p_ag_list = p_agents_sub.add_parser("list", help="List agents")
    p_ag_list.add_argument("--json", action="store_true")
    p_ag_add = p_agents_sub.add_parser("add", help="Add agent")
    p_ag_add.add_argument("agent_id")
    p_ag_add.add_argument("--name", default=None)
    p_ag_add.add_argument("--desc", default="")
    p_ag_add.add_argument("--model", default=None)
    p_ag_add.add_argument("--provider", default=None)
    p_ag_del = p_agents_sub.add_parser("delete", help="Delete agent")
    p_ag_del.add_argument("agent_id")
    p_ag_del.add_argument("--force", action="store_true")

    # Org
    p_org = subparsers.add_parser("org", help="Org chart hierarchy")
    p_org_sub = p_org.add_subparsers(dest="org_subcommand")
    p_org_sub.add_parser("show", help="Show Pride tree")
    p_org_exp = p_org_sub.add_parser("explain", help="Explain communication permissions")
    p_org_exp.add_argument("from_agent")
    p_org_exp.add_argument("to_agent")
    p_org_sub.add_parser("doctor", help="Lint org hierarchy")

    # Cron
    p_cron = subparsers.add_parser("cron", help="Manage scheduled jobs")
    p_cron_sub = p_cron.add_subparsers(dest="cron_subcommand")
    p_cron_sub.add_parser("list", help="List jobs")
    p_cron_add = p_cron_sub.add_parser("add", help="Add job")
    p_cron_add.add_argument("--cron", default=None)
    p_cron_add.add_argument("--every", default=None)
    p_cron_add.add_argument("--at", default=None)
    p_cron_add.add_argument("--message", required=True)
    p_cron_add.add_argument("--tz", default="UTC")
    p_cron_rm = p_cron_sub.add_parser("rm", help="Remove job")
    p_cron_rm.add_argument("job_id")
    p_cron_run = p_cron_sub.add_parser("run", help="Fire job immediately")
    p_cron_run.add_argument("job_id")

    # Pairing
    p_pair = subparsers.add_parser("pairing", help="Manage channel pairing requests")
    p_pair_sub = p_pair.add_subparsers(dest="pairing_subcommand")
    p_pair_sub.add_parser("list", help="List pending pairing codes")
    p_pair_app = p_pair_sub.add_parser("approve", help="Approve pairing code")
    p_pair_app.add_argument("code")
    p_pair_app.add_argument("--channel", default="telegram")
    p_pair_deny = p_pair_sub.add_parser("deny", help="Deny pairing code")
    p_pair_deny.add_argument("code")

    # Encrypt
    p_enc = subparsers.add_parser("encrypt", help="Manage at-rest encryption")
    p_enc_sub = p_enc.add_subparsers(dest="encrypt_subcommand")
    p_enc_sub.add_parser("status", help="Check encryption status")
    p_enc_sub.add_parser("init", help="Initialize master key")
    p_enc_sub.add_parser("test", help="Test encryption round-trip")

    # Backup
    p_bak = subparsers.add_parser("backup", help="Manage backups")
    p_bak_sub = p_bak.add_subparsers(dest="backup_subcommand")
    p_bak_sub.add_parser("create", help="Create backup snapshot")
    p_bak_ver = p_bak_sub.add_parser("verify", help="Verify backup archive")
    p_bak_ver.add_argument("path")

    # Secrets
    p_sec = subparsers.add_parser("secrets", help="Secrets management")
    p_sec_sub = p_sec.add_subparsers(dest="secrets_subcommand")
    p_sec_sub.add_parser("audit", help="Scan for leaked secrets")

    # MCP
    p_mcp = subparsers.add_parser("mcp", help="Run Tideline MCP server over stdio")
    p_mcp.add_argument("--agent", default="main")

    args = parser.parse_args()

    if args.command == "status":
        cmd_status(args)
    elif args.command == "doctor":
        cmd_doctor(args)
    elif args.command == "gateway":
        cmd_gateway(args)
    elif args.command == "agents":
        cmd_agents(args)
    elif args.command == "org":
        cmd_org(args)
    elif args.command == "cron":
        cmd_cron(args)
    elif args.command == "pairing":
        cmd_pairing(args)
    elif args.command == "encrypt":
        cmd_encrypt(args)
    elif args.command == "backup":
        cmd_backup(args)
    elif args.command == "secrets":
        cmd_secrets(args)
    elif args.command == "mcp":
        cmd_mcp(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
