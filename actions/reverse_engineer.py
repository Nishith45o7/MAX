"""
actions/reverse_engineer.py
Binary analysis, code analysis, system monitoring, diagrams, security scanning.
Inspired by rea, diagram-design, gods-eye-view.
"""
import ast, dis, hashlib, io, json, logging, os, re, struct, time
from pathlib import Path
logger = logging.getLogger("reverse_engineer")

def _desktop():
    for p in [Path.home()/"Desktop", Path.home()/"OneDrive"/"Desktop"]:
        if p.exists(): return p
    return Path.home()/"Desktop"

def reverse_engineer(parameters: dict, player=None) -> str:
    action = (parameters.get("action") or "system_monitor").strip().lower()
    aliases = {
        "binary": "analyze_binary", "code": "analyze_code", "monitor": "system_monitor",
        "diagram": "generate_diagram", "diagrams": "generate_diagram", "deps": "dependency_graph",
        "security": "security_scan", "scan": "security_scan", "hex": "hex_dump",
        "decompile": "decompile_python"
    }
    action = aliases.get(action, action)

    if action == "analyze_binary":
        path = (parameters.get("path") or parameters.get("file_path") or "").strip()
        if not path or not Path(path).exists():
            return f"File not found: {path}"
        fp = Path(path)
        data = fp.read_bytes()
        # Magic bytes detection
        sigs = {b"MZ": "PE/EXE", b"\x7fELF": "ELF", b"PK": "ZIP/JAR", b"\x89PNG": "PNG",
                b"\xff\xd8": "JPEG", b"GIF8": "GIF", b"%PDF": "PDF", b"Rar": "RAR"}
        ftype = "Unknown"
        for sig, name in sigs.items():
            if data[:len(sig)] == sig:
                ftype = name; break
        # Extract strings
        strings = re.findall(rb"[\x20-\x7e]{4,}", data[:50000])
        top_strings = [s.decode("ascii", errors="ignore") for s in strings[:20]]
        # PE info
        pe_info = ""
        if ftype == "PE/EXE" and len(data) > 64:
            try:
                e_lfanew = struct.unpack_from("<I", data, 60)[0]
                if data[e_lfanew:e_lfanew+2] == b"PE":
                    machine = struct.unpack_from("<H", data, e_lfanew+4)[0]
                    arch = {0x14c: "x86", 0x8664: "x64", 0xaa64: "ARM64"}.get(machine, hex(machine))
                    sections = struct.unpack_from("<H", data, e_lfanew+6)[0]
                    pe_info = f"\n  • Architecture: {arch}\n  • Sections: {sections}"
            except: pass
        return (f"🔍 Binary Analysis: {fp.name}\n"
                f"  • Type: {ftype}\n  • Size: {len(data):,} bytes\n"
                f"  • SHA-256: {hashlib.sha256(data).hexdigest()[:32]}...{pe_info}\n"
                f"  • Strings ({len(strings)} found, top 10):\n" +
                "\n".join(f"    {s[:80]}" for s in top_strings[:10]))

    elif action == "analyze_code":
        code = parameters.get("code") or ""
        path = (parameters.get("path") or parameters.get("file_path") or "").strip()
        filename = "code snippet"
        if not code and path:
            if not Path(path).exists():
                return f"File not found: {path}"
            code = Path(path).read_text("utf-8", errors="ignore")
            filename = Path(path).name
        if not code:
            return "Please provide either 'code' text or a valid 'file_path'."
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return f"Syntax error in {filename}: {e}"
        classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        imports = []
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                imports.extend(a.name for a in n.names)
            elif isinstance(n, ast.ImportFrom) and n.module:
                imports.append(n.module)
        lines = code.splitlines()
        return (f"📊 Code Analysis: {Path(path).name}\n"
                f"  • Lines: {len(lines)} ({sum(1 for l in lines if l.strip()):,} non-blank)\n"
                f"  • Classes ({len(classes)}): {', '.join(classes[:10]) or 'none'}\n"
                f"  • Functions ({len(funcs)}): {', '.join(funcs[:15]) or 'none'}\n"
                f"  • Imports ({len(imports)}): {', '.join(sorted(set(imports))[:15])}")

    elif action == "system_monitor":
        import psutil
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/") if os.name != "nt" else psutil.disk_usage("C:\\")
        boot = time.time() - psutil.boot_time()
        uptime_h = int(boot // 3600)
        procs = sorted(psutil.process_iter(["name","cpu_percent","memory_percent"]),
                       key=lambda p: p.info.get("cpu_percent",0) or 0, reverse=True)[:5]
        top = "\n".join(f"    • {p.info['name']}: CPU {p.info.get('cpu_percent',0):.1f}% / MEM {p.info.get('memory_percent',0):.1f}%"
                        for p in procs)
        return (f"🖥️ System Monitor:\n"
                f"  • CPU: {cpu}%\n  • RAM: {mem.percent}% ({mem.used/1e9:.1f}/{mem.total/1e9:.1f} GB)\n"
                f"  • Disk: {disk.percent}% ({disk.used/1e9:.1f}/{disk.total/1e9:.1f} GB)\n"
                f"  • Uptime: {uptime_h}h {int((boot%3600)//60)}m\n"
                f"  • Top Processes:\n{top}")

    elif action == "process_tree":
        import psutil
        procs = list(psutil.process_iter(["pid","name","ppid","cpu_percent","memory_percent"]))
        procs.sort(key=lambda p: p.info.get("memory_percent",0) or 0, reverse=True)
        lines = [f"🌳 Process Tree (top 25 by memory):\n"]
        for p in procs[:25]:
            lines.append(f"  PID {p.info['pid']:>6} | {p.info['name']:<25} | CPU {p.info.get('cpu_percent',0):5.1f}% | MEM {p.info.get('memory_percent',0):5.1f}%")
        return "\n".join(lines)

    elif action == "generate_diagram":
        path = (parameters.get("path") or "").strip()
        if not path or not Path(path).exists():
            return f"File not found: {path}"
        code = Path(path).read_text("utf-8", errors="ignore")
        try:
            tree = ast.parse(code)
        except:
            return "Could not parse file."
        mermaid = ["classDiagram"]
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                mermaid.append(f"    class {node.name} {{")
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        mermaid.append(f"        +{item.name}()")
                mermaid.append("    }")
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        mermaid.append(f"    {base.id} <|-- {node.name}")
        if len(mermaid) < 2:
            mermaid = ["flowchart TD"]
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    mermaid.append(f"    {node.name}[{node.name}]")
        diagram = "\n".join(mermaid)
        out = _desktop() / f"diagram_{Path(path).stem}.mmd"
        out.write_text(diagram, "utf-8")
        return f"📐 Diagram generated → {out}\n\n```mermaid\n{diagram}\n```"

    elif action == "dependency_graph":
        path = (parameters.get("path") or "").strip()
        if not path:
            return "Path to project or requirements.txt required."
        fp = Path(path)
        if fp.name == "requirements.txt" and fp.exists():
            deps = [l.split(">=")[0].split("==")[0].strip() for l in fp.read_text("utf-8").splitlines() if l.strip() and not l.startswith("#")]
            mermaid = "flowchart LR\n    Project --> " + "\n    Project --> ".join(deps)
        elif fp.is_dir():
            imports = set()
            for pyf in fp.rglob("*.py"):
                try:
                    tree = ast.parse(pyf.read_text("utf-8", errors="ignore"))
                    for n in ast.walk(tree):
                        if isinstance(n, ast.Import):
                            for a in n.names: imports.add(a.name.split(".")[0])
                        elif isinstance(n, ast.ImportFrom) and n.module:
                            imports.add(n.module.split(".")[0])
                except: pass
            mermaid = "flowchart LR\n" + "\n".join(f"    Project --> {i}" for i in sorted(imports)[:30])
        else:
            return f"Not found: {path}"
        out = _desktop() / "dependency_graph.mmd"
        out.write_text(mermaid, "utf-8")
        return f"📐 Dependency graph → {out}\n\n```mermaid\n{mermaid}\n```"

    elif action == "security_scan":
        path = (parameters.get("path") or "").strip()
        if not path or not Path(path).exists():
            return f"Not found: {path}"
        fp = Path(path)
        files = list(fp.rglob("*.py")) if fp.is_dir() else [fp]
        issues = []
        patterns = [
            (r'\beval\s*\(', "Use of eval()"), (r'\bexec\s*\(', "Use of exec()"),
            (r'\bos\.system\s*\(', "Use of os.system()"), (r'\bsubprocess\.call\s*\(.*shell\s*=\s*True', "Shell injection risk"),
            (r'(?i)(password|secret|api_key|token)\s*=\s*["\'][^"\']{3,}', "Hardcoded credential"),
            (r'\bpickle\.load', "Unsafe pickle deserialization"), (r'\bmarshal\.load', "Unsafe marshal load"),
            (r'(?i)SELECT\s+.*\+\s*["\']', "Potential SQL injection"),
        ]
        for pyf in files[:50]:
            try:
                code = pyf.read_text("utf-8", errors="ignore")
                for i, line in enumerate(code.splitlines(), 1):
                    for pat, desc in patterns:
                        if re.search(pat, line):
                            issues.append(f"  ⚠️ {pyf.name}:{i} — {desc}")
            except: pass
        if not issues:
            return f"✅ Security scan clean: {len(files)} files checked, no issues found."
        return f"🔒 Security Scan ({len(issues)} issues in {len(files)} files):\n" + "\n".join(issues[:30])

    elif action == "hex_dump":
        path = (parameters.get("path") or "").strip()
        n = int(parameters.get("bytes", 256))
        if not path or not Path(path).exists():
            return f"Not found: {path}"
        data = Path(path).read_bytes()[:n]
        lines = [f"🔢 Hex Dump: {Path(path).name} (first {len(data)} bytes)\n"]
        for i in range(0, len(data), 16):
            chunk = data[i:i+16]
            hex_part = " ".join(f"{b:02x}" for b in chunk).ljust(48)
            ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
            lines.append(f"  {i:08x}  {hex_part}  |{ascii_part}|")
        return "\n".join(lines)

    elif action == "api_map":
        path = (parameters.get("path") or "").strip()
        if not path or not Path(path).exists():
            return f"Not found: {path}"
        fp = Path(path)
        files = list(fp.rglob("*.py")) if fp.is_dir() else [fp]
        routes = []
        for pyf in files:
            try:
                code = pyf.read_text("utf-8", errors="ignore")
                for m in re.finditer(r'@\w+\.(get|post|put|delete|patch|route)\s*\(\s*["\']([^"\']+)', code):
                    routes.append(f"  {m.group(1).upper():>6} {m.group(2)}  ({pyf.name})")
            except: pass
        if not routes:
            return "No API routes found."
        return f"🗺️ API Map ({len(routes)} routes):\n" + "\n".join(routes)

    elif action == "decompile_python":
        path = (parameters.get("path") or "").strip()
        if not path or not Path(path).exists():
            return f"Not found: {path}"
        if path.endswith(".pyc"):
            try:
                import marshal, struct as st
                data = Path(path).read_bytes()
                code_obj = marshal.loads(data[16:])
                buf = io.StringIO()
                dis.dis(code_obj, file=buf)
                return f"🔧 Bytecode disassembly of {Path(path).name}:\n{buf.getvalue()[:3000]}"
            except Exception as e:
                return f"Decompile failed: {e}"
        else:
            code = Path(path).read_text("utf-8", errors="ignore")
            compiled = compile(code, path, "exec")
            buf = io.StringIO()
            dis.dis(compiled, file=buf)
            return f"🔧 Bytecode of {Path(path).name}:\n{buf.getvalue()[:3000]}"

    else:
        return (f"Unknown action '{action}'. Available: analyze_binary, analyze_code, system_monitor, "
                "process_tree, generate_diagram, dependency_graph, security_scan, hex_dump, api_map, decompile_python")

if __name__ == "__main__":
    print(reverse_engineer({"action": "system_monitor"}))

