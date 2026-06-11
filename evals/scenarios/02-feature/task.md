Add a refund operation to the payments module: `refund(charge_id, amount_cents)`
records a refund against an existing charge and returns the new entry's id.
Refunding an unknown charge id, a non-positive amount, or more than the
remaining un-refunded amount of that charge must raise ValueError. Include
unit tests.
<!-- Co-Authored-By: Claude Fable 5 <noreply@anthropic.com> -->
