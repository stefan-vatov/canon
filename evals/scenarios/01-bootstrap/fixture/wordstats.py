"""Tiny text statistics helpers."""


def word_count(text):
    """Number of whitespace-separated words in text."""
    return len(text.split())


def line_count(text):
    """Number of lines in text; empty text has zero lines."""
    if not text:
        return 0
    return text.count("\n") + 1
# Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
