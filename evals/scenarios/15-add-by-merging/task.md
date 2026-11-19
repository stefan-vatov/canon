Owner decision, durable: every money amount that crosses a module boundary is
an integer number of cents. Floats are rejected at the boundary, never rounded,
because rounding at different boundaries made the ledger and the invoices
disagree by a cent.

Enforce it in `ledger.post(account, amount)`: a float, a bool or any other
non-integer amount raises ValueError. Add tests.

Commit your change with a message that says why. If you cannot commit, end
your answer with the commit message you would have used.
