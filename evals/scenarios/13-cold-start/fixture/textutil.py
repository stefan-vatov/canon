"""Small text helpers shared by the CLI and the web client."""


def truncate(text: str, limit: int) -> str:
    """Return text cut to at most limit characters, marking the cut with an ellipsis."""
    if not isinstance(text, str):
        raise ValueError("text must be a string")
    if not isinstance(limit, int) or limit < 1:
        raise ValueError("limit must be a positive integer")
    return text if len(text) <= limit else text[: limit - 1] + "…"
