Decision, durable: all user-visible timestamps in reports are UTC, formatted
as ISO-8601 with a trailing "Z". We considered showing each user's local
timezone and rejected it — support tickets quoting local times across
timezones were impossible to correlate.

Implement `format_timestamp(dt)` in reports.py: accepts a timezone-aware
datetime, converts to UTC, returns the "YYYY-MM-DDTHH:MM:SSZ" string. Naive
datetimes raise ValueError. Add tests.
<!-- Co-Authored-By: Claude Fable 5 <noreply@anthropic.com> -->
