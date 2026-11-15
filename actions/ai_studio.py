"""
actions/ai_studio.py
Multi-modal AI generation hub — images, avatars, ad copy, TTS, memes.
Inspired by Open-Generative-AI, Open-LLM-VTuber, claude-ads, Handy.
"""

import json
import logging
import os
import time
import urllib.parse
from pathlib import Path
from typing import Optional

logger = logging.getLogger("ai_studio")
USER_AGENT = "MAX-MARK-I/1.0"


def _desktop() -> Path:
    for p in [Path.home() / "Desktop", Path.home() / "OneDrive" / "Desktop"]:
        if p.exists():
            return p
    return Path.home() / "Desktop"


def ai_studio(parameters: dict, player=None) -> str:
    """AI creative studio."""
    action = (parameters.get("action") or "generate_image").strip().lower()
    aliases = {
        "image": "generate_image", "avatar": "generate_avatar", "ad_copy": "generate_ad_copy",
        "ad": "generate_ad_copy", "tts": "text_to_speech", "speech": "text_to_speech",
        "style": "style_transfer", "upscale": "upscale_image", "bg_remove": "remove_background",
        "video_frames": "generate_video_frames", "brief": "creative_brief", "meme": "meme_generator"
    }
    action = aliases.get(action, action)

    if action == "generate_image":
        prompt = (parameters.get("prompt") or "").strip()
        if not prompt:
            return "Image prompt is required."
        style = (parameters.get("style") or "").strip()
        size = (parameters.get("size") or "square").strip().lower()
        sizes = {"square": (1024, 1024), "landscape": (1920, 1080), "portrait": (1080, 1920), "social": (1080, 1080), "banner": (1200, 630)}
        w, h = sizes.get(size, (1024, 1024))
        if style:
            prompt = f"{prompt}, {style} style"
        try:
            import requests
            encoded = urllib.parse.quote(prompt)
            url = f"https://image.pollinations.ai/prompt/{encoded}?width={w}&height={h}&nologo=true"
            resp = requests.get(url, timeout=45)
            if resp.status_code == 200:
                fname = f"ai_gen_{int(time.time())}.png"
                out = _desktop() / fname
                out.write_bytes(resp.content)
                return f"🎨 Image generated → {out}\n  Prompt: {prompt}\n  Size: {w}x{h}"
            return f"Generation returned status {resp.status_code}."
        except Exception as e:
            return f"Image generation failed: {e}"

    elif action == "generate_avatar":
        description = (parameters.get("description") or parameters.get("prompt", "")).strip()
        if not description:
            return "Avatar description is required."
        style = (parameters.get("style") or "professional").strip()
        prompt = f"Professional portrait headshot of {description}, {style} style, clean background, high quality, studio lighting"
        try:
            import requests
            encoded = urllib.parse.quote(prompt)
            url = f"https://image.pollinations.ai/prompt/{encoded}?width=512&height=512&nologo=true"
            resp = requests.get(url, timeout=45)
            if resp.status_code == 200:
                fname = f"avatar_{int(time.time())}.png"
                out = _desktop() / fname
                out.write_bytes(resp.content)
                return f"👤 Avatar generated → {out}\n  Style: {style}"
            return f"Avatar generation returned status {resp.status_code}."
        except Exception as e:
            return f"Avatar generation failed: {e}"

    elif action == "generate_ad_copy":
        product = (parameters.get("product") or parameters.get("name", "")).strip()
        audience = (parameters.get("audience") or "general consumers").strip()
        tone = (parameters.get("tone") or "professional").strip()
        platform = (parameters.get("platform") or "social media").strip()
        if not product:
            return "Product/service name is required."
        try:
            from or_client import client as or_client
            prompt = (
                f"Generate marketing ad copy for:\n"
                f"Product: {product}\nTarget Audience: {audience}\n"
                f"Tone: {tone}\nPlatform: {platform}\n\n"
                f"Generate:\n1. Headline (max 10 words)\n2. Subheadline\n"
                f"3. Body copy (2-3 sentences)\n4. Call to action\n5. 5 relevant hashtags"
            )
            result = or_client.chat(prompt, system="You are an expert marketing copywriter. Be creative, concise, and persuasive.")
            return f"📢 Ad Copy for '{product}':\n\n{result}"
        except Exception as e:
            return (
                f"📢 Ad Copy Template for '{product}':\n\n"
                f"🔥 Headline: Discover {product} — Designed for {audience}\n"
                f"📝 Subheadline: The smartest choice for {audience} who value quality.\n"
                f"💡 Body: Experience the difference with {product}. Built with cutting-edge technology "
                f"and designed for real results. Join thousands of satisfied users today.\n"
                f"👉 CTA: Get Started Free Today!\n"
                f"#️⃣ #{product.replace(' ', '')} #Innovation #SmartChoice #TopRated #MustHave\n\n"
                f"(LLM unavailable for custom copy: {e})"
            )

    elif action == "text_to_speech":
        text = (parameters.get("text") or "").strip()
        if not text:
            return "Text is required for TTS."
        lang = (parameters.get("language") or "en").strip()
        try:
            import requests
            tts_url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl={lang}&client=tw-ob&q={urllib.parse.quote(text[:200])}"
            resp = requests.get(tts_url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code == 200 and len(resp.content) > 1000:
                fname = f"tts_{int(time.time())}.mp3"
                out = _desktop() / fname
                out.write_bytes(resp.content)
                return f"🔊 TTS audio saved → {out}"
        except Exception:
            pass
        try:
            import pyttsx3
            engine = pyttsx3.init()
            fname = f"tts_{int(time.time())}.mp3"
            out = _desktop() / fname
            engine.save_to_file(text, str(out))
            engine.runAndWait()
            return f"🔊 TTS audio saved (local engine) → {out}"
        except Exception:
            pass
        return "TTS failed. Install pyttsx3 for local TTS: pip install pyttsx3"

    elif action == "style_transfer":
        prompt = (parameters.get("prompt") or "").strip()
        style = (parameters.get("style") or "oil painting").strip()
        if not prompt:
            return "Description/prompt is required."
        full_prompt = f"{prompt}, rendered in {style} artistic style, masterpiece quality"
        try:
            import requests
            encoded = urllib.parse.quote(full_prompt)
            url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&nologo=true"
            resp = requests.get(url, timeout=45)
            if resp.status_code == 200:
                fname = f"styled_{int(time.time())}.png"
                out = _desktop() / fname
                out.write_bytes(resp.content)
                return f"🎨 Style transfer complete → {out}\n  Style: {style}"
            return f"Style transfer returned status {resp.status_code}."
        except Exception as e:
            return f"Style transfer failed: {e}"

    elif action == "upscale_image":
        path = (parameters.get("path") or "").strip()
        scale = int(parameters.get("scale", 2))
        if not path or not Path(path).exists():
            return f"Image file not found: {path}"
        try:
            from PIL import Image
            img = Image.open(path)
            new_size = (img.width * scale, img.height * scale)
            upscaled = img.resize(new_size, Image.LANCZOS)
            out = _desktop() / f"upscaled_{scale}x_{Path(path).name}"
            upscaled.save(str(out), quality=95)
            return f"⬆️ Upscaled {scale}x: {img.width}x{img.height} → {new_size[0]}x{new_size[1]} → {out}"
        except ImportError:
            return "Pillow not installed."
        except Exception as e:
            return f"Upscale failed: {e}"

    elif action == "remove_background":
        path = (parameters.get("path") or "").strip()
        if not path or not Path(path).exists():
            return f"Image file not found: {path}"
        try:
            from rembg import remove
            from PIL import Image
            img = Image.open(path)
            output = remove(img)
            out = _desktop() / f"nobg_{Path(path).stem}.png"
            output.save(str(out))
            return f"✅ Background removed → {out}"
        except ImportError:
            return "rembg not installed. Run: pip install rembg"
        except Exception as e:
            return f"Background removal failed: {e}"

    elif action == "generate_video_frames":
        prompt = (parameters.get("prompt") or "").strip()
        frames = int(parameters.get("frames", 4))
        if not prompt:
            return "Base prompt is required."
        import requests
        out_dir = _desktop() / f"frames_{int(time.time())}"
        out_dir.mkdir(parents=True, exist_ok=True)
        saved = []
        for i in range(frames):
            frame_prompt = f"{prompt}, frame {i+1} of {frames}, cinematic sequence"
            try:
                encoded = urllib.parse.quote(frame_prompt)
                url = f"https://image.pollinations.ai/prompt/{encoded}?width=1280&height=720&nologo=true&seed={42+i}"
                resp = requests.get(url, timeout=45)
                if resp.status_code == 200:
                    out_f = out_dir / f"frame_{i+1:03d}.png"
                    out_f.write_bytes(resp.content)
                    saved.append(str(out_f))
            except Exception:
                pass
        return f"🎬 Generated {len(saved)}/{frames} video frames → {out_dir}"

    elif action == "creative_brief":
        project = (parameters.get("project") or parameters.get("name", "")).strip()
        description = (parameters.get("description") or "").strip()
        if not project:
            return "Project name is required."
        try:
            from or_client import client as or_client
            prompt = f"Create a comprehensive creative brief for: {project}\nDetails: {description}\nInclude: Objectives, Target Audience, Key Messages, Tone & Style, Deliverables, Timeline, Success Metrics."
            result = or_client.chat(prompt, system="You are a senior creative director. Create detailed, actionable creative briefs.")
            return f"📋 Creative Brief: {project}\n\n{result}"
        except Exception:
            return (
                f"📋 Creative Brief: {project}\n\n"
                f"🎯 Objectives: Define clear goals for {project}\n"
                f"👥 Target Audience: Identify key demographics\n"
                f"💬 Key Messages: Core value propositions\n"
                f"🎨 Tone & Style: Visual and verbal identity\n"
                f"📦 Deliverables: List all required assets\n"
                f"📅 Timeline: Set milestones and deadlines\n"
                f"📊 Success Metrics: KPIs to track\n\n"
                f"(Configure OpenRouter for AI-generated detailed briefs)"
            )

    elif action == "meme_generator":
        top_text = (parameters.get("top_text") or "").strip()
        bottom_text = (parameters.get("bottom_text") or "").strip()
        prompt = (parameters.get("prompt") or "funny meme background").strip()
        if not top_text and not bottom_text:
            return "At least top_text or bottom_text is required."
        try:
            import requests
            from PIL import Image, ImageDraw, ImageFont
            from io import BytesIO
            encoded = urllib.parse.quote(prompt)
            url = f"https://image.pollinations.ai/prompt/{encoded}?width=800&height=800&nologo=true"
            resp = requests.get(url, timeout=45)
            if resp.status_code == 200:
                img = Image.open(BytesIO(resp.content))
                draw = ImageDraw.Draw(img)
                try:
                    font = ImageFont.truetype("arial.ttf", 40)
                except Exception:
                    font = ImageFont.load_default()
                def draw_text(text, y_pos):
                    bbox = draw.textbbox((0, 0), text, font=font)
                    tw = bbox[2] - bbox[0]
                    x = (img.width - tw) // 2
                    for dx, dy in [(-2, -2), (2, -2), (-2, 2), (2, 2)]:
                        draw.text((x + dx, y_pos + dy), text, fill="black", font=font)
                    draw.text((x, y_pos), text, fill="white", font=font)
                if top_text:
                    draw_text(top_text.upper(), 20)
                if bottom_text:
                    draw_text(bottom_text.upper(), img.height - 70)
                out = _desktop() / f"meme_{int(time.time())}.png"
                img.save(str(out))
                return f"😂 Meme generated → {out}"
        except ImportError:
            return "Pillow not installed."
        except Exception as e:
            return f"Meme generation failed: {e}"

    else:
        return (
            f"Unknown action '{action}'. Available: generate_image, generate_avatar, "
            "generate_ad_copy, text_to_speech, style_transfer, upscale_image, "
            "remove_background, generate_video_frames, creative_brief, meme_generator"
        )


if __name__ == "__main__":
    print(ai_studio({"action": "generate_ad_copy", "product": "MAX AI Assistant"}))

