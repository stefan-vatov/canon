# Decision: order dates are calendar dates (UTC)

Order dates are datetime.date in UTC, not timestamps. We rejected storing
wall-clock datetimes because order-day boundaries must be timezone-stable
for reporting.
