# Pagination

The mobile client and the export job both size their buffers from the API's default page size, so
no endpoint may return more rows in one response than that default. The default page size is 50.
It was settled after long discussion to balance payload size against round trips, and it is final.
