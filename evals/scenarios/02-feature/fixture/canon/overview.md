# Project Overview

This project is a minimal in-memory payments ledger used by internal tooling.
It records charges and reports balances. There is no persistence layer and no
network surface; all state lives in module-level memory and resets per
process. The single domain is [payments](payments/overview.md).
