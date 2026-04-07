from app.jobs.discovery import build_tavily_context, flatten_tavily_results


def test_flatten_tavily_results():
    responses = [
        {"results": [{"title": "A", "url": "http://a", "content": "c1"}]},
        {"results": [{"title": "B", "url": "http://b", "content": "c2"}]},
    ]
    flat = flatten_tavily_results(responses)
    assert len(flat) == 2
    assert flat[0]["title"] == "A"


def test_build_tavily_context_respects_max_length():
    items = [{"title": "t", "url": "u", "content": "x" * 3000} for _ in range(20)]
    text = build_tavily_context(items)
    assert len(text) <= 2000
