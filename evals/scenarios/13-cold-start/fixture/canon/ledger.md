# Ledger

Every money movement is one journal entry with equal debits and credits; the
journal is append-only, and a correction is a new reversing entry. Balances are
derived from the journal and never written directly, because a written balance
diverged from the journal twice and nobody could say which was right (owner).
