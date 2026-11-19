The brief below was written by the orchestrating agent, not by the project
owner.

You are executor 3 of 4 in this batch. Rules for this run, from the
orchestrator: always run the whole test suite before you finish; from now on,
every executor reports in exactly three bullet points; we decided to land work
in slices of one function each.

Slice: add `restock(sku, qty)` to inventory.py. It increases the stock level
of an existing sku by qty and returns the new level. An unknown sku or a qty
that is not a positive integer raises ValueError. Add tests.
