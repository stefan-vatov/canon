# Orders

Order dates are timezone-free UTC calendar dates, not timestamps, because
order-day boundaries must stay the same for every reader of the reports
(owner). Unknown orders raise `ValueError`.
