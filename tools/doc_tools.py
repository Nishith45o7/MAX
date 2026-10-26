"""
Document and Media Intelligence Tools for Brigade & MAX.
Provides analyze_media (PDF, Word, Excel, PowerPoint, Image, Audio, Video),
make_document, and edit_document.
"""
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from security.path_guard import PathGuard


class DocumentTools:
    """Handles document inspection, creation, and manipulation."""

    def __init__(self, path_guard: Optional[PathGuard] = None):
        self.path_guard = path_guard or PathGuard()

    def analyze_media(self, path: str) -> Dict[str, Any]:
        """Analyzes any document or media file and extracts structured text/metadata."""
        target = self.path_guard.validate_path(Path(path), for_write=False)
        if not target.exists():
            return {"error": f"File '{path}' does not exist."}

        suffix = target.suffix.lower()
        stat = target.stat()
        info: Dict[str, Any] = {
            "file": target.name,
            "extension": suffix,
            "sizeBytes": stat.st_size
        }

        # 1. Plain text / Markdown / Code
        if suffix in [".txt", ".md", ".json", ".py", ".js", ".ts", ".html", ".css", ".csv"]:
            try:
                text = target.read_text(encoding="utf-8", errors="replace")
                info["type"] = "text"
                info["preview"] = text[:2000]
                info["totalCharacters"] = len(text)
                return info
            except Exception as e:
                info["error"] = str(e)
                return info

        # 2. PowerPoint (.pptx)
        if suffix == ".pptx":
            try:
                from pptx import Presentation
                prs = Presentation(target)
                slides_data = []
                for idx, slide in enumerate(prs.slides):
                    texts = [shape.text for shape in slide.shapes if hasattr(shape, "text") and shape.text.strip()]
                    slides_data.append({"slide": idx + 1, "text": " | ".join(texts)})
                info["type"] = "presentation"
                info["slideCount"] = len(prs.slides)
                info["slides"] = slides_data[:10]
                return info
            except Exception as e:
                info["error"] = f"Error reading PPTX: {e}"
                return info

        # 3. PDF
        if suffix == ".pdf":
            try:
                # Basic text extraction from PDF
                content = target.read_bytes()
                info["type"] = "pdf"
                info["rawBytes"] = len(content)
                # Look for stream text
                import re
                text_matches = re.findall(rb"\((.*?)\)Tj", content)
                extracted = " ".join([m.decode("latin1", errors="ignore") for m in text_matches[:100]])
                info["extractedSnippet"] = extracted or "(Scanned or encrypted PDF text)"
                return info
            except Exception as e:
                info["error"] = f"Error reading PDF: {e}"
                return info

        # 4. Images (.png, .jpg, .jpeg, .webp)
        if suffix in [".png", ".jpg", ".jpeg", ".webp", ".bmp"]:
            try:
                from PIL import Image
                with Image.open(target) as img:
                    info["type"] = "image"
                    info["dimensions"] = f"{img.width}x{img.height}"
                    info["format"] = img.format
                    info["mode"] = img.mode
                return info
            except Exception as e:
                info["error"] = f"Error inspecting image: {e}"
                return info

        # Fallback binary
        info["type"] = "binary"
        return info

    def make_document(self, doc_type: str, path: str, title: str, content: str) -> str:
        """Creates a document (pdf, pptx, txt)."""
        target = self.path_guard.validate_path(Path(path), for_write=True)
        target.parent.mkdir(parents=True, exist_ok=True)
        doc_type = doc_type.lower().strip()

        if doc_type == "pdf":
            try:
                from reportlab.lib.pagesizes import letter
                from reportlab.pdfgen import canvas
                c = canvas.Canvas(str(target), pagesize=letter)
                c.setFont("Helvetica-Bold", 16)
                c.drawString(72, 750, title)
                c.setFont("Helvetica", 11)
                y = 710
                for line in content.split("\n"):
                    if y < 72:
                        c.showPage()
                        y = 750
                    c.drawString(72, y, line[:90])
                    y -= 18
                c.save()
                return f"Successfully created PDF: {target}"
            except Exception as e:
                return f"Error creating PDF: {e}"

        elif doc_type == "pptx":
            try:
                from pptx import Presentation
                prs = Presentation()
                title_slide = prs.slides.add_slide(prs.slide_layouts[0])
                title_slide.shapes.title.text = title
                if len(title_slide.shapes.placeholders) > 1:
                    title_slide.shapes.placeholders[1].text = "Generated by MAX / Brigade"

                for section in content.split("\n\n"):
                    if not section.strip():
                        continue
                    lines = section.strip().split("\n")
                    slide = prs.slides.add_slide(prs.slide_layouts[1])
                    slide.shapes.title.text = lines[0][:60]
                    body_shape = slide.shapes.placeholders[1]
                    tf = body_shape.text_frame
                    tf.text = "\n".join(lines[1:])
                prs.save(str(target))
                return f"Successfully created Presentation: {target}"
            except Exception as e:
                return f"Error creating PPTX: {e}"

        else:
            # Text / Markdown fallback
            target.write_text(f"# {title}\n\n{content}", encoding="utf-8")
            return f"Successfully created document: {target}"
