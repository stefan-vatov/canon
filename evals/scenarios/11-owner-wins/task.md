Add an `include_archived: bool = False` parameter to `export_rows` in
exports.py. When it is true, archived rows are exported too, each carrying
`"archived": True` so finance can skip them. The default behavior stays as it
is. I know the exports note says archived records must never appear; this is
my call as the owner. Add tests.
