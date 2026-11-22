# Ticket reservation

Python and PostgreSQL service for selling numbered seats.

If two buyers go for the last seat, only one hold is stored. The hold is written in a transaction and it expires. Sending the same request again does not book that seat a second time.

Short pull requests add the tables, the hold and confirm flow, and tests for a race and for a cancelled hold.
