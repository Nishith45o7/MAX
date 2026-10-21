from duckduckgo_search import DDGS

def search_web(query: str, max_results: int = 5) -> str:
    """Searches DuckDuckGo and returns clean text results."""
    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append(f"Title: {r['title']}\nSnippet: {r['body']}\nURL: {r['href']}")
        
        if not results:
            return "No web results found."
        return "\n\n---\n\n".join(results)
    except Exception as e:
        return f"Search error: {str(e)}"

# Quick test when running this file directly
if __name__ == "__main__":
    test_query = "latest AI news 2026"
    print(f"Testing search for: {test_query}\n")
    print(search_web(test_query))