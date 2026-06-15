Decision: the default API page size is 50 — used when a client does not
specify one. Rationale: it balances payload size against round-trips. Record
this decision, then add `default_page_size()` to pagination.py returning it.
Add a test.
<!-- Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com> -->
