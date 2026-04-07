"""Pure helpers for supplier discovery (testable without Tavily network calls)."""

MAX_CONTEXT_CHARS = 2000
CONTENT_SNIPPET_LEN = 500


def flatten_tavily_results(responses: list[dict]) -> list[dict]:
    """Each response is the full Tavily API dict (must include 'results' list)."""
    out: list[dict] = []
    for resp in responses:
        for item in resp.get("results") or []:
            out.append(item)
    return out


def build_tavily_context(search_result_items: list[dict]) -> str:
    """Build a bounded text blob for the LLM from Tavily search hits."""
    parts: list[str] = []
    total = 0
    for item in search_result_items:
        title = str(item.get("title") or "")
        url = str(item.get("url") or "")
        content = str(item.get("content") or "")[:CONTENT_SNIPPET_LEN]
        chunk = f"Title: {title}\nURL: {url}\nContent: {content}\n---\n"
        if total + len(chunk) > MAX_CONTEXT_CHARS:
            break
        parts.append(chunk)
        total += len(chunk)
    return "\n".join(parts)
