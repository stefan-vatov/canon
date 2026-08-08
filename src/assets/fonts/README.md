# Newsreader Variable (vendored, instanced)

Source: `@fontsource-variable/newsreader` 5.3.0 (SIL Open Font License, see
LICENSE). Files are the package's opsz woff2 subsets with the weight axis
instanced to the range the site actually uses:

    fonttools varLib.instancer <subset>.woff2 wght=400:700

The `opsz` axis (6–72) is untouched — `font-optical-sizing: auto` depends on
it. Unicode subsets (latin, latin-ext, vietnamese) and their `unicode-range`
mappings in `global.css` are copied from the package verbatim, so glyph
coverage is unchanged; browsers download only the subsets a page uses.

If the site ever needs weights outside 400–700, re-instance from the package
with a wider range and update the `font-weight` descriptors in `global.css`.
