# Glossary

- cents -> all money amounts, always integer cents; there is no decimal or
  float money representation anywhere in the system
- ledger entry -> one dict in the ledger with keys `id`, `kind`,
  `amount_cents`; `kind` is the entry type, e.g. `charge`
- balance -> sum of charge amounts minus non-charge amounts, in cents
