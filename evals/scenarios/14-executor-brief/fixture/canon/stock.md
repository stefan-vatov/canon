# Stock

Stock levels are never negative. The warehouse system and the storefront both
read levels from `inventory`, so a level change is visible to both at once.
