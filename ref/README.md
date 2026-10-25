# ref/ — the shadcn/ui reference grid (dev-only)

This is the oracle that alder-ui's parity check diffs against: a Vite + React + shadcn/ui
app (new-york-v4 registry, Tailwind v4, the canonical neutral theme, Geist) that renders
every compared component, variant and state once, with fixed text. `test/parity.py` loads
`ref/dist/index.html` next to `demo/parity.html` (the same grid built from alder-ui
elements) and compares computed styles marker by marker.

**Node is never needed to build or test alder-ui.** The build output, `dist/`, is
committed, so the parity check needs only Python, Playwright and a browser. Node is used
here, and only here, to regenerate that output when shadcn changes.

## What the page contains

- Every compared element carries `data-ref="<component>/<variant>/<state-or-size>"`;
  `data-ref-states="hover focus"` lists the states the harness drives; overlays carry
  `data-ref-open` and are rendered open.
- `<html data-ref-ready>` is set once every marker exists (some are tagged after mount:
  the table wrapper, the dialog close button, the tooltip arrow, the sonner toasts) and the
  fonts have loaded. Wait for it, then for the 150–200ms enter animations.
- `#dark` puts `.dark` on `<html>` for humans; the harness toggles the class itself, and
  sonner's theme follows the class.
- Fonts: Geist and Geist Mono (OFL) from `../fonts/` in this repository, declared with
  `@font-face` in `src/index.css`; Vite copies them into `dist/assets/`, so `dist/` is
  self-contained.

## Layout: the reference follows the twin

`demo/parity.html` may not use `<style>` or `style=`; it lays out with
`<al-page width="wide">` and `<al-stack>` only. So the reference reproduces the twin's
containing blocks, not the other way round (ruling R1):

- the frame is `al-page width="wide"`: max-width 80rem, border-box, centred, padding
  2rem 1rem, padding-inline 1.5rem from 40rem. At the harness's 1280px viewport the
  content column is 1232px;
- sections stack like a column `al-stack` (flex column, children stretch), so block
  controls (inputs, textareas, cards, alerts, tables, tabs) are 1232px wide;
- intrinsic controls (buttons, badges, checkboxes, the select trigger, pagination) sit in
  row stacks (flex row, wrap, items centred) and keep their own width.

Overlays sit in stages at the end of the page so they cover no other marker. The dialog is
non-modal (a modal Radix dialog traps focus and disables pointer events on `<body>`, which
would stop the harness driving the other markers); its content node is moved into a box
with a transform, so `position: fixed` resolves against that box, and its overlay is drawn
there with shadcn's DialogOverlay class string (Radix renders the overlay only for modal
dialogs). Popover, menu and tooltip are anchored to their triggers with collision
avoidance off. Sonner's toaster renders in place inside its own transformed stage, expanded.
When widths still mismatch the twin, fix the reference layout here and rebuild.

## Regenerating

From `ref/`:

```sh
npm ci
npx shadcn@4.22.1 add button input textarea label select checkbox card badge alert table \
  pagination dialog popover dropdown-menu tooltip sonner tabs separator --overwrite
npm run build
```

Then commit `dist/` (and any changed `src/components/ui/*.tsx`, `package*.json`) and
re-run `python3 test/parity.py` from the repository root. Bump the pinned shadcn version
deliberately: when a recipe class string changes, amend the companion reference file in
the Alder repository (`docs/superpowers/specs/2026-10-24-alder-ui-shadcn-reference.md`,
"Ref §3") with a dated note rather than editing the generated `.tsx`.

`components.json` is written by hand (style `new-york`, base colour neutral, CSS
variables on): `shadcn init` in CLI 4.x only offers the newer presets, while
`style: "new-york"` with Tailwind v4 makes `add` fetch the new-york-v4 registry. For the
same reason `src/index.css` is written by hand: the canonical `:root`/`.dark` sheet from
ui.shadcn.com/themes verbatim (`--radius: 0.625rem`), the `@theme inline` colour and
radius scale, shadcn's base layer, the Geist `@font-face`s and the font stacks.

To look at it: `python3 -m http.server 8000` from the repository root, then
`http://localhost:8000/ref/dist/` and `http://localhost:8000/ref/dist/#dark`.
