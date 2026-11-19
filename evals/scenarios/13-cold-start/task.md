Add `slugify(text)` to textutil.py: lowercase the text, replace each run of
characters that are not ASCII letters or digits with a single hyphen, and
strip leading and trailing hyphens. Non-string input raises ValueError. Add
tests.
