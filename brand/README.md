# Brand

- `og.html` — source for `public/og.png` (1200×630). Regenerate after edits:

  ```sh
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
    --headless=new --disable-gpu --hide-scrollbars --virtual-time-budget=4000 \
    --window-size=1200,630 --screenshot=public/og.png brand/og.html
  ```

- The mark is a **stone arch** — a voussoir ring on plinthed piers, the
  keystone articulated by two angled masonry joints, spring-line joints
  where the ring meets the piers. The companion project's mark is the pen
  (the instrument that writes the law); Canon's is the arch (the structure
  that stays standing): it holds because the keystone holds — "the
  implementation churns, the canon holds" — and it is also the gate every
  change passes through (§ III). Joints are overprinted in the ground
  color and dropped at tiny sizes, where the solid silhouette carries.
- There is deliberately **no ratification-style seal**: ratification is the
  companion project's ritual, and Canon has none — the record starts empty
  and
  grows page by page, its authority carried by front matter
  (`status: normative`) and the doctor's gate. Where a large emblem is
  wanted (the meta-strip, the OG corner), the mark appears as a plain
  **printer's device** (`src/components/ArchMark.astro`) — the press's
  emblem on a colophon: it declares provenance, it certifies nothing.
- The mark lives inline where it is used: `public/favicon.svg`,
  `src/components/SiteHeader.astro`, `SiteFooter.astro`, `ArchMark.astro`,
  and `brand/og.html` — all share the same 100-unit geometry
  (viewBox `4 8 92 88`: outer ring R36 / opening r16, spring line y52,
  plinths y82–90; joint strokes thicken slightly as the render shrinks).
  Icon PNGs (`icon-192`, `icon-512`, `apple-touch-icon`) are headless-Chrome
  screenshots of `public/favicon.svg` at 192/512/180 px with a transparent
  background (`--default-background-color=00000000`).
