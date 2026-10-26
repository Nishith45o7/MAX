import urllib.parse
import requests
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger("web_tool")

def search_web(query: str, max_results: int = 5) -> str:
    """
    Robust multi-tiered web search:
    1. Try ddgs news if news/time sensitive.
    2. Try ddgs text.
    3. Fallback to direct DuckDuckGo HTML scraping.
    """
    results = []
    clean_query = query.strip()
    is_news_query = any(w in clean_query.lower() for w in ["news", "today", "latest", "stock", "trade", "market", "update", "current"])

    # Attempt 1: ddgs news if time-sensitive
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            if is_news_query:
                news_items = list(ddgs.news(clean_query, max_results=max_results))
                for r in news_items:
                    results.append(f"Title: {r.get('title')}\nSnippet: {r.get('body')}\nURL: {r.get('url')}\nSource: {r.get('source')}")
            if not results:
                for r in ddgs.text(clean_query, max_results=max_results):
                    results.append(f"Title: {r.get('title')}\nSnippet: {r.get('body')}\nURL: {r.get('href')}")
    except Exception as e:
        logger.warning(f"DDGS primary search failed ({e}), attempting fallback...")

    # Attempt 2: HTML scraper fallback (ultra-reliable, no JS required)
    if not results:
        try:
            url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(clean_query)}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9"
            }
            resp = requests.get(url, headers=headers, timeout=8)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                blocks = soup.select(".web-result") or soup.select(".result")
                for b in blocks[:max_results]:
                    title_elem = b.select_one(".result__title") or b.select_one("a.result__url")
                    snippet_elem = b.select_one(".result__snippet")
                    link_elem = b.select_one(".result__url") or b.select_one("a")
                    
                    title = title_elem.get_text(strip=True) if title_elem else "No title"
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                    link = link_elem.get("href", "") if link_elem else ""
                    if snippet or title:
                        results.append(f"Title: {title}\nSnippet: {snippet}\nURL: {link}")
        except Exception as fe:
            logger.error(f"HTML scraper fallback failed: {fe}")

    if not results:
        return f"No direct web results found for '{query}'. Please try rephrasing or specify a market/country."

    return "\n\n---\n\n".join(results)

if __name__ == "__main__":
    test_q = "today trade news"
    print(f"Testing search for: {test_q}\n")
    print(search_web(test_q))