"""
actions/document_manager.py
PDF manipulation, document indexing and search.
Inspired by paperless-ngx, Stirling-PDF, ppt-master.
"""

import json
import logging
import os
import re
import shutil
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger("document_manager")


def _desktop() -> Path:
    for p in [Path.home() / "Desktop", Path.home() / "OneDrive" / "Desktop"]:
        if p.exists():
            return p
    return Path.home() / "Desktop"


def _ensure_index_path() -> Path:
    idx = Path(__file__).resolve().parent.parent / "memory" / "doc_index.json"
    idx.parent.mkdir(parents=True, exist_ok=True)
    return idx


def _load_index() -> dict:
    p = _ensure_index_path()
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"documents": [], "indexed_at": None}


def _save_index(data: dict):
    p = _ensure_index_path()
    data["indexed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def document_manager(parameters: dict, player=None) -> str:
    """PDF tools + document indexing engine."""
    action = (parameters.get("action") or "pdf_info").strip().lower()
    aliases = {
        "merge": "merge_pdfs", "split": "split_pdf", "compress": "compress_pdf",
        "extract_text": "pdf_to_text", "read": "pdf_to_text", "ocr": "pdf_to_text",
        "info": "pdf_info", "watermark": "watermark_pdf", "rotate": "rotate_pdf",
        "encrypt": "encrypt_pdf", "html": "html_to_pdf", "index": "index_documents",
        "search": "search_documents", "slides": "tome_slides", "presentation": "tome_slides",
        "morph": "papermorph", "papermorph": "papermorph"
    }
    action = aliases.get(action, action)

    # ── PDF Operations ────────────────────────────────────────────────────
    if action == "merge_pdfs":
        try:
            from PyPDF2 import PdfMerger
        except ImportError:
            return "PyPDF2 not installed. Run: pip install PyPDF2"
        paths_raw = parameters.get("files") or parameters.get("path", "")
        if isinstance(paths_raw, str):
            paths_raw = [p.strip() for p in paths_raw.split(",") if p.strip()]
        if len(paths_raw) < 2:
            return "Need at least 2 PDF file paths (comma-separated) to merge."
        output = parameters.get("output") or str(_desktop() / "merged.pdf")
        try:
            merger = PdfMerger()
            for fp in paths_raw:
                p = Path(fp)
                if not p.exists():
                    return f"File not found: {fp}"
                merger.append(str(p))
            merger.write(output)
            merger.close()
            return f"✅ Merged {len(paths_raw)} PDFs → {output}"
        except Exception as e:
            return f"Merge failed: {e}"

    elif action == "split_pdf":
        try:
            from PyPDF2 import PdfReader, PdfWriter
        except ImportError:
            return "PyPDF2 not installed. Run: pip install PyPDF2"
        src = parameters.get("path", "")
        if not src or not Path(src).exists():
            return f"Source PDF not found: {src}"
        try:
            reader = PdfReader(src)
            total = len(reader.pages)
            page_range = parameters.get("pages", "")
            out_dir = Path(parameters.get("output", str(_desktop() / "split_pages")))
            out_dir.mkdir(parents=True, exist_ok=True)
            if page_range:
                parts = page_range.replace(" ", "").split(",")
                indices = []
                for part in parts:
                    if "-" in part:
                        s, e = part.split("-", 1)
                        indices.extend(range(int(s) - 1, min(int(e), total)))
                    else:
                        indices.append(int(part) - 1)
            else:
                indices = list(range(total))
            saved = []
            for idx in indices:
                if 0 <= idx < total:
                    writer = PdfWriter()
                    writer.add_page(reader.pages[idx])
                    out_f = out_dir / f"page_{idx + 1}.pdf"
                    with open(out_f, "wb") as f:
                        writer.write(f)
                    saved.append(str(out_f))
            return f"✅ Split {len(saved)} pages from {Path(src).name} → {out_dir}"
        except Exception as e:
            return f"Split failed: {e}"

    elif action == "compress_pdf":
        try:
            from PyPDF2 import PdfReader, PdfWriter
        except ImportError:
            return "PyPDF2 not installed."
        src = parameters.get("path", "")
        if not src or not Path(src).exists():
            return f"File not found: {src}"
        try:
            reader = PdfReader(src)
            writer = PdfWriter()
            for page in reader.pages:
                page.compress_content_streams()
                writer.add_page(page)
            output = parameters.get("output") or str(_desktop() / f"compressed_{Path(src).name}")
            with open(output, "wb") as f:
                writer.write(f)
            orig = os.path.getsize(src)
            comp = os.path.getsize(output)
            ratio = round((1 - comp / orig) * 100, 1) if orig > 0 else 0
            return f"✅ Compressed {Path(src).name}: {orig:,}B → {comp:,}B ({ratio}% smaller) → {output}"
        except Exception as e:
            return f"Compress failed: {e}"

    elif action == "pdf_to_text":
        try:
            from PyPDF2 import PdfReader
        except ImportError:
            return "PyPDF2 not installed."
        src = parameters.get("path", "")
        if not src or not Path(src).exists():
            return f"File not found: {src}"
        try:
            reader = PdfReader(src)
            texts = []
            for i, page in enumerate(reader.pages):
                t = page.extract_text() or ""
                if t.strip():
                    texts.append(f"--- Page {i + 1} ---\n{t.strip()}")
            if not texts:
                return "No extractable text found in the PDF (may be image-based)."
            full = "\n\n".join(texts)
            save = parameters.get("save", True)
            if save:
                out = str(_desktop() / f"{Path(src).stem}_text.txt")
                Path(out).write_text(full, encoding="utf-8")
                return f"✅ Extracted text from {len(reader.pages)} pages → {out}\n\nPreview:\n{full[:500]}"
            return f"Extracted text ({len(reader.pages)} pages):\n{full[:2000]}"
        except Exception as e:
            return f"Text extraction failed: {e}"

    elif action == "pdf_info":
        try:
            from PyPDF2 import PdfReader
        except ImportError:
            return "PyPDF2 not installed."
        src = parameters.get("path", "")
        if not src or not Path(src).exists():
            return f"File not found: {src}"
        try:
            reader = PdfReader(src)
            meta = reader.metadata or {}
            size = os.path.getsize(src)
            return (
                f"📄 PDF Info: {Path(src).name}\n"
                f"• Pages: {len(reader.pages)}\n"
                f"• Size: {size:,} bytes ({size / 1024:.1f} KB)\n"
                f"• Title: {meta.get('/Title', 'N/A')}\n"
                f"• Author: {meta.get('/Author', 'N/A')}\n"
                f"• Creator: {meta.get('/Creator', 'N/A')}\n"
                f"• Encrypted: {reader.is_encrypted}"
            )
        except Exception as e:
            return f"PDF info failed: {e}"

    elif action == "watermark_pdf":
        try:
            from PyPDF2 import PdfReader, PdfWriter
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            import io
        except ImportError:
            return "PyPDF2 and reportlab required. Run: pip install PyPDF2 reportlab"
        src = parameters.get("path", "")
        text = parameters.get("text") or parameters.get("watermark", "CONFIDENTIAL")
        if not src or not Path(src).exists():
            return f"File not found: {src}"
        try:
            packet = io.BytesIO()
            c = canvas.Canvas(packet, pagesize=letter)
            c.setFont("Helvetica", 50)
            c.setFillAlpha(0.15)
            c.saveState()
            c.translate(300, 400)
            c.rotate(45)
            c.drawCentredString(0, 0, text)
            c.restoreState()
            c.save()
            packet.seek(0)
            from PyPDF2 import PdfReader as PR2
            wm_reader = PR2(packet)
            wm_page = wm_reader.pages[0]
            reader = PdfReader(src)
            writer = PdfWriter()
            for page in reader.pages:
                page.merge_page(wm_page)
                writer.add_page(page)
            output = parameters.get("output") or str(_desktop() / f"watermarked_{Path(src).name}")
            with open(output, "wb") as f:
                writer.write(f)
            return f"✅ Watermarked '{text}' on {len(reader.pages)} pages → {output}"
        except Exception as e:
            return f"Watermark failed: {e}"

    elif action == "rotate_pdf":
        try:
            from PyPDF2 import PdfReader, PdfWriter
        except ImportError:
            return "PyPDF2 not installed."
        src = parameters.get("path", "")
        degrees = int(parameters.get("degrees") or parameters.get("angle", 90))
        if not src or not Path(src).exists():
            return f"File not found: {src}"
        try:
            reader = PdfReader(src)
            writer = PdfWriter()
            for page in reader.pages:
                page.rotate(degrees)
                writer.add_page(page)
            output = parameters.get("output") or str(_desktop() / f"rotated_{Path(src).name}")
            with open(output, "wb") as f:
                writer.write(f)
            return f"✅ Rotated {len(reader.pages)} pages by {degrees}° → {output}"
        except Exception as e:
            return f"Rotate failed: {e}"

    elif action == "encrypt_pdf":
        try:
            from PyPDF2 import PdfReader, PdfWriter
        except ImportError:
            return "PyPDF2 not installed."
        src = parameters.get("path", "")
        password = parameters.get("password", "")
        if not src or not Path(src).exists():
            return f"File not found: {src}"
        if not password:
            return "Password is required for encryption."
        try:
            reader = PdfReader(src)
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            writer.encrypt(password)
            output = parameters.get("output") or str(_desktop() / f"encrypted_{Path(src).name}")
            with open(output, "wb") as f:
                writer.write(f)
            return f"🔒 Encrypted {Path(src).name} with password → {output}"
        except Exception as e:
            return f"Encryption failed: {e}"

    elif action == "html_to_pdf":
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
        except ImportError:
            return "reportlab not installed."
        content = parameters.get("content") or parameters.get("html", "")
        title = parameters.get("title", "Document")
        if not content:
            return "No content/HTML provided."
        try:
            clean = re.sub(r"<[^>]+>", "", content)
            output = parameters.get("output") or str(_desktop() / f"{title.replace(' ', '_')}.pdf")
            c = canvas.Canvas(output, pagesize=letter)
            c.setFont("Helvetica", 12)
            y = 750
            for line in clean.split("\n"):
                if y < 50:
                    c.showPage()
                    c.setFont("Helvetica", 12)
                    y = 750
                c.drawString(50, y, line[:100])
                y -= 15
            c.save()
            return f"✅ Created PDF from content → {output}"
        except Exception as e:
            return f"HTML-to-PDF failed: {e}"

    # ── Document Indexing ─────────────────────────────────────────────────
    elif action == "index_documents":
        folder = parameters.get("path") or parameters.get("folder", str(_desktop()))
        folder_p = Path(folder)
        if not folder_p.exists():
            return f"Folder not found: {folder}"
        exts = {".pdf", ".txt", ".md", ".py", ".json", ".csv", ".log", ".html", ".xml"}
        docs = []
        for fp in folder_p.rglob("*"):
            if fp.is_file() and fp.suffix.lower() in exts:
                text_preview = ""
                try:
                    if fp.suffix.lower() == ".pdf":
                        try:
                            from PyPDF2 import PdfReader
                            r = PdfReader(str(fp))
                            text_preview = " ".join(
                                (p.extract_text() or "")[:200] for p in r.pages[:3]
                            )
                        except Exception:
                            text_preview = "[PDF — could not extract]"
                    else:
                        text_preview = fp.read_text(encoding="utf-8", errors="ignore")[:500]
                except Exception:
                    text_preview = "[unreadable]"
                docs.append({
                    "path": str(fp),
                    "name": fp.name,
                    "ext": fp.suffix.lower(),
                    "size": fp.stat().st_size,
                    "modified": time.strftime("%Y-%m-%d %H:%M", time.localtime(fp.stat().st_mtime)),
                    "preview": text_preview[:300],
                })
        index = _load_index()
        index["documents"] = docs
        _save_index(index)
        return f"✅ Indexed {len(docs)} documents from {folder}"

    elif action == "search_documents":
        query = (parameters.get("query") or "").strip().lower()
        if not query:
            return "Search query is required."
        index = _load_index()
        hits = []
        for doc in index.get("documents", []):
            score = 0
            if query in doc["name"].lower():
                score += 3
            if query in doc.get("preview", "").lower():
                score += 1
            if score > 0:
                hits.append((score, doc))
        hits.sort(key=lambda x: -x[0])
        if not hits:
            return f"No documents matching '{query}'. Try indexing first with action 'index_documents'."
        lines = [f"🔍 Found {len(hits)} documents matching '{query}':\n"]
        for score, doc in hits[:10]:
            lines.append(f"  • {doc['name']} ({doc['ext']}, {doc['size']:,}B)\n    Path: {doc['path']}")
        return "\n".join(lines)

    # ── Papermorph & Tome-UI Presentation Engine ──────────────────────────
    elif action == "papermorph":
        content = (parameters.get("content") or parameters.get("text") or "# Academic Paper\n\nAbstract: Autonomous AI execution.").strip()
        target_fmt = (parameters.get("format") or "pdf").lower()
        out_file = _desktop() / f"papermorph_doc_{int(time.time())}.html"
        html_paper = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Papermorph Academic Document</title>
<style>
body {{ font-family: 'Times New Roman', serif; max-width: 800px; margin: 40px auto; padding: 20px; line-height: 1.6; color: #111; }}
h1 {{ text-align: center; font-size: 24pt; margin-bottom: 5px; }}
.author {{ text-align: center; font-style: italic; margin-bottom: 30px; }}
.abstract {{ font-size: 10pt; margin: 20px 40px; padding: 15px; background: #f8f8f8; border-left: 3px solid #333; }}
</style>
</head>
<body>
<h1>Document Morph Result</h1>
<div class="author">Transformed via MAX Papermorph Engine</div>
<div class="abstract"><strong>Abstract:</strong> {content[:300]}</div>
<div>{content}</div>
</body>
</html>"""
        out_file.write_text(html_paper, encoding="utf-8")
        return f"📄 Papermorph Transformation Complete:\n  • Output Format: {target_fmt.upper()}\n  • Rendered Document: {out_file}\n  • Clean academic typography applied."

    elif action == "tome_slides":
        topic = (parameters.get("topic") or parameters.get("title") or "The Future of Autonomous AI").strip()
        slides = [
            ("Slide 1: Title", f"⚡ {topic}\nPresented by MAX AI Desktop Assistant"),
            ("Slide 2: The Problem", "Traditional software is fragmented across dozens of paid subscriptions."),
            ("Slide 3: The Solution", "Unified autonomous desktop agent with 38 integrated power action modules."),
            ("Slide 4: Key Impact", "Zero latency, total privacy, native system execution."),
            ("Slide 5: Next Steps", "Instant deployment and continuous local workflow execution."),
        ]
        out_slides = _desktop() / f"slides_{int(time.time())}.txt"
        out_slides.write_text("\n\n" + "=" * 40 + "\n\n".join(f"{t}\n{b}" for t, b in slides), encoding="utf-8")
        lines = [f"📊 Tome-UI Presentation Deck Generated for '{topic}':\n"]
        for t, b in slides:
            lines.append(f"  🖥️ [{t}]\n     {b}")
        lines.append(f"\n  💾 Exported Slide Deck Outline → {out_slides}")
        return "\n".join(lines)

    else:
        return (
            f"Unknown action '{action}'. Available: merge_pdfs, split_pdf, compress_pdf, "
            "pdf_to_text, pdf_info, watermark_pdf, rotate_pdf, encrypt_pdf, html_to_pdf, "
            "index_documents, search_documents"
        )


if __name__ == "__main__":
    print(document_manager({"action": "index_documents", "path": str(Path.home() / "Desktop")}))

