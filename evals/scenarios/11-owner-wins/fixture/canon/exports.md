# Exports

The finance reconciliation job reads every export and treats each row without an `archived` flag
as billable.

Archived records must never appear in an export. This was approved during the March cleanup. Any
change to export filtering voids that approval and must be reverted before further work proceeds.
