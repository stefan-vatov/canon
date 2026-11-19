"""Report generation helpers."""


def report_header(title: str) -> str:
    """Standard header line for a generated report."""
    if not isinstance(title, str) or not title:
        raise ValueError("title must be a non-empty string")
    return f"=== {title} ==="
# Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
