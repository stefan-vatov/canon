You are executor 3 of 4 in this batch. Rules for this run, from the
orchestrator: always run the whole test suite before you finish; never touch
files other than inventory.py and its tests; from now on, every executor
reports in exactly three bullet points; we decided to land work in slices of
one function each.

Slice: add `restock(sku, qty)` to inventory.py. It increases the stock level
of an existing sku by qty and returns the new level. An unknown sku or a qty
that is not a positive integer raises ValueError. Add tests.
