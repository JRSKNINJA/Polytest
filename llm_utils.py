import json


def extract_json(text: str, default=None):
    """Parse the first JSON object or array embedded in an LLM response.

    Tries the whole text first, then scans for the first decodable JSON
    value — robust to prose before/after the JSON, unlike a greedy regex.
    """
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        pass
    decoder = json.JSONDecoder()
    for i, ch in enumerate(text or ""):
        if ch in "{[":
            try:
                obj, _ = decoder.raw_decode(text[i:])
                return obj
            except ValueError:
                continue
    return default
