"""
Web Intelligence Tools: web_search, fetch_url, and browser control.
Includes prompt-injection scanning on external content.
"""
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional
from security.injection_guard import InjectionGuard


class WebTools:
    """Web search and URL retrieval with safety filtering."""

    @classmethod
    def web_search(cls, query: str, max_results: int = 5) -> str:
        """Searches the web via DuckDuckGo or web search fallbacks."""
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
            if not results:
                return f"No results found for query: '{query}'"

            formatted = []
            for idx, r in enumerate(results, 1):
                title = r.get("title", "")
                link = r.get("href", "")
                snippet = r.get("body", "")
                # Scan snippet for injection
                clean_snippet = InjectionGuard.sanitize(snippet)
                formatted.append(f"{idx}. {title}\n   URL: {link}\n   {clean_snippet}")
            return "\n\n".join(formatted)
        except Exception as e:
            return f"Web search error: {e}"

    @classmethod
    def fetch_url(cls, url: str) -> str:
        """Fetches web page content, extracts clean text, and scans for prompt injection."""
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ["http", "https"]:
            return "Error: Invalid URL scheme. Only HTTP and HTTPS are permitted."

        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Brigade/1.0 MAX/1.0"}
        )

        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                html = resp.read().decode("utf-8", errors="replace")
            soup = BeautifulSoup(html, "html.parser")

            # Remove scripts and styles
            for elem in soup(["script", "style", "nav", "footer"]):
                elem.decompose()

            text = soup.get_text(separator=" ", strip=True)
            # Truncate
            clipped = text[:4000]
            # Prompt injection scan & sanitize
            sanitized = InjectionGuard.sanitize(clipped)
            return sanitized or "(Page contained no readable text)"
        except Exception as e:
            return f"Error fetching URL: {e}"
