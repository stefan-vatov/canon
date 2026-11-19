"""Pagination helpers. Page sizes are positive integers."""

DEFAULT_PAGE_SIZE = 50


def default_page_size() -> int:
    """Page size used when a client does not ask for one."""
    return DEFAULT_PAGE_SIZE


def page_count(total_items: int, page_size: int) -> int:
    """Number of pages needed for total_items at page_size."""
    if not isinstance(total_items, int) or total_items < 0:
        raise ValueError("total_items must be a non-negative integer")
    if not isinstance(page_size, int) or page_size <= 0:
        raise ValueError("page_size must be a positive integer")
    return (total_items + page_size - 1) // page_size
