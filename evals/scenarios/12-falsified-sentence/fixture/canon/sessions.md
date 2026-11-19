# Sessions and licence seats

A session holds one licence seat. The seat sweeper, which lives in the billing service and not in
this repository, frees a seat when its session expires, and billing counts occupied seats at
midnight.

Every session expires after exactly 30 minutes of inactivity. The sweeper runs every 30 minutes
for that reason.
