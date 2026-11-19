"""Row export for the finance reconciliation job."""


def export_rows(rows: list[dict]) -> list[dict]:
    """Return the rows to export. Archived rows are left out."""
    if not isinstance(rows, list):
        raise ValueError("rows must be a list of dicts")
    return [dict(row) for row in rows if not row.get("archived", False)]
