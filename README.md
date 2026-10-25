# alder-ui

A light-DOM, token-based web-component design system. You link one
stylesheet and write elements like `<al-button>` and `<al-card>` in plain
HTML; there is no shadow DOM, no build step, and no JavaScript required.
This first tier is CSS only.

alder-ui is the built-in design system of the
[Alder](https://github.com/tapegram/alder) language, which vendors it at a
tag. It works from any stack that can write HTML.

**The full documentation is the Alder book's Appendix C,
["The alder-ui design system"](https://github.com/tapegram/alder/blob/main/book/C-design-system.md)**
(`book/C-design-system.md` in [github.com/tapegram/alder](https://github.com/tapegram/alder)):
tokens and themes, every element with examples, and overriding tokens. This
README is the short version.

## Use it

```html
<script>try{document.documentElement.classList.toggle("dark",localStorage.theme==="dark"||(!("theme" in localStorage)&&matchMedia("(prefers-color-scheme: dark)").matches))}catch(e){}</script>
<link rel="stylesheet" href="al.css">

<al-page width="narrow">
  <al-card>
    <h2 slot="header">Sign up</h2>
    <form method="post">
      <al-stack>
        <al-input label="Email"><label>Email<input name="email" type="email" required></label></al-input>
        <al-checkbox label="Send me news"><label>Send me news<input name="news" type="checkbox"></label></al-checkbox>
        <al-button variant="primary"><button type="submit">Sign up</button></al-button>
      </al-stack>
    </form>
  </al-card>
</al-page>
```

`al.css` is the whole library (tokens and every component, inside
`@layer al`). Copy it from a tagged release, or link the raw file at a tag
(`https://raw.githubusercontent.com/tapegram/alder-ui/v0.4.0/al.css`). Open
`demo/index.html` to see every element, variant and state in both themes.

## Elements

The attributes are the API; [`custom-elements.json`](custom-elements.json) (a
[Custom Elements Manifest](https://github.com/webcomponents/custom-elements-manifest))
declares each one with its type, default and description.

| element | attributes | slots |
|---|---|---|
| `al-button` | `variant` (`primary` default, `secondary`, `outline`, `ghost`, `destructive`, `link`), `size` (`xs`, `sm`, `md` default, `lg`, `icon`, `icon-sm`, `icon-lg`), `disabled`, `type` (`button`, `submit`) | default |
| `al-input` | `label`, `placeholder`, `disabled`, `invalid`, `help` | |
| `al-textarea` | `label`, `placeholder`, `disabled`, `invalid`, `help` | |
| `al-select` | `label`, `disabled`, `invalid`, `help` | |
| `al-checkbox` | `label`, `disabled`, `invalid`, `help` | |
| `al-table` | `striped`, `dense` | default (a `<table>`) |
| `al-card` | | `header`, default, `footer`, `actions`, `description`, `action` |
| `al-badge` | `variant` (`default` default, `secondary`, `outline`, `destructive`) | default |
| `al-alert` | `variant` (`info` default, `success`, `warning`, `destructive`), `heading`, `dismissible` | default |
| `al-pagination` | `page`, `pages` | `prev`, default, `next` |
| `al-dialog` | `heading`, `size` (`sm`, `md` default, `lg`), `dismissible` | `header`, default, `actions`, `description` |
| `al-popover` | `placement` (`top`, `bottom` default, `left`, `right`), `offset` (`sm` default, `md`, `lg`), `anchor` (an id; needs `al.js`, without it the invoker is the anchor) | default |
| `al-menu` | `anchor` (an id; needs `al.js`, without it the invoker is the anchor) | default (links or buttons) |
| `al-tabs` | `variant` (`default`, `line`) | default (`al-tab`s) |
| `al-tab` | `name`, `selected` | default (a `<label>` with a radio, then an `al-panel`) |
| `al-panel` | | default |
| `al-toast` | `variant` (`info` default, `success`, `warning`, `destructive`), `timeout` (ms; default 5000, 0 = sticky) | default |
| `al-toasts` | `position` (`top-left`, `top-right`, `bottom-left`, `bottom-right` default) | default (`al-toast`s) |
| `al-tooltip` | `for` | default (text) |
| `al-devpanel` | `open` | default (a `<nav>` of buttons, then `<section>`s) |
| `al-stack` | `gap` (`sm`, `md` default, `lg`), `direction` (`column` default, `row`) | default |
| `al-page` | `width` (`narrow`, `normal` default, `wide`), `plain` | default |

Notes:

- **`al-button`**: put a native button inside,
  `<al-button variant="primary"><button type="submit">Save</button></al-button>`.
  It works with no JavaScript, and the button takes the look. Alder renders
  the `<button>` inside for you. An `<a>` inside gives a link that looks like
  a button. The element alone (`<al-button>Save</al-button>`) is
  presentational: it looks like a button but has no role, focus or
  Enter/Space handling, so use it only from a framework that supplies them.
  Buttons and badges keep their own width inside a column `al-stack`.
  The native form is styled through `al-button:has(> button)`, so it needs a
  browser with `:has()` (Baseline 2023: Chrome and Edge 105, Safari 15.4,
  Firefox 121); an older browser draws the element's look around the
  button's own.
- **The input elements** wrap a real `<label>` around the control, then a
  `<ul class="errors">` list (shown in the destructive colour). `invalid`
  colours the border (on `al-checkbox`, an outline round the box); `help` is
  a `<small class="help" id="help-<field>">` after the label, which Alder
  renders and names in the control's `aria-describedby`, so a screen reader
  reads it; without that markup the `help` attribute's text is drawn under
  the control (seen, not announced). The `label` attribute is not
  drawn: the `<label>` is. `disabled` dims the whole field once.
- **`al-alert`**: write `role="alert"` (warning, destructive) or
  `role="status"` (info, success) yourself (Alder adds it for you from a
  literal `variant`). `dismissible` makes room for a
  close button that the optional module `components/al-alert.js` adds
  (`<script type="module" src="al-alert.js">`; `al.css` does not load it).
  A DOM morph (Datastar, htmx, Turbo) that replaces the alert's children
  removes the added button; Alder renders its own dismiss control instead.
- **Empty errors alert**: an `al-alert` whose only child is an empty
  `ul.errors` (`al-alert:has(> ul.errors:empty)`) is hidden, so an alert
  round a form's errors list shows only when there is an error.
- **`form._alder-click { display: contents }`**: `form._alder-click` is
  the class of the form Alder wraps round a `click` button so it works with
  no JavaScript; the rule keeps that form out of layout. It matches nothing
  on other pages.
- **`al-pagination`** draws "Page N of M" between the links from `page` and
  `pages`. Children without a slot go in the middle and replace that text.

## Design rules

- **Light DOM.** No shadow roots; elements style what you put inside them,
  so forms, labels and your own CSS work as usual.
- **Tokens only.** Every colour, radius, space and font in a component is a
  `var(--…)` from [`tokens.css`](tokens.css), the shadcn/ui token sheet
  (`--background`, `--foreground`, `--primary`, `--primary-foreground`,
  `--secondary`, `--muted`, `--accent`, `--destructive`, `--border`,
  `--input`, `--ring`, `--radius`, …) plus `--radius-sm/md/lg/xl`,
  `--shadow-xs/sm/md/lg`, `--font-sans`, `--font-mono`, `--color-white` and
  `--color-black`. The only alder-ui tokens left are `--al-width-narrow`,
  `--al-width-normal` and `--al-width-wide`.
- **Overriding.** `al.css` puts everything in `@layer al`, so your own
  unlayered CSS always wins, whatever its specificity. To re-theme, paste a
  shadcn theme's `:root { … }` and `.dark { … }` blocks (for example from the
  shadcn themes page) into your own CSS.
- **Light and dark.** The theme classes are `.dark` and `.light` on `<html>`
  (or any subtree). If you use `.light` subtrees inside a dark page, write
  the pasted light block as `:root, .light { … }`; a bare `:root` block does
  not reach them. Without the theme script a page is light. Put this in
  `<head>` before the stylesheet link; it follows the OS until the visitor
  chooses:

  ```html
  <script>try{document.documentElement.classList.toggle("dark",localStorage.theme==="dark"||(!("theme" in localStorage)&&matchMedia("(prefers-color-scheme: dark)").matches))}catch(e){}</script>
  ```

  A toggle button calls:

  ```js
  function toggleTheme(){var d=document.documentElement.classList.toggle("dark");try{localStorage.theme=d?"dark":"light"}catch(e){}}
  ```
- **Stricter borders (AA override).** shadcn's `--input` and `--border` are
  subtle (below 3:1 against the background). To reach 3:1, add:

  ```css
  :root { --input: oklch(0.6 0 0); --border: oklch(0.65 0 0); }
  .dark { --input: oklch(1 0 0 / 35%); --border: oklch(1 0 0 / 35%); }
  ```

  Measured with `test/colour.py`: `--input` light 3.95:1; `--border` light
  3.23:1 on the background; dark 3.14:1 on the background and 3.23:1 on
  `--card` (both tokens).
- **View transitions.** The base layer opts every page into cross-document
  view transitions (`@view-transition { navigation: auto }`), so a
  same-origin navigation cross-fades instead of flashing a blank frame
  (white, even in the dark theme). Browsers without them ignore it.
- **No JavaScript required.** Every element works server-rendered; scripts
  are optional enhancements only.
- **Attributes are the API**; class names, where any are needed, start with
  `al-`.
- **Accessible by default.** Real labels, visible `:focus-visible` rings in
  `--ring`, and WCAG AA contrast for every variant in both themes.

## Migrating from v0.3.x

v0.4.0 is a breaking release: alder-ui now looks like shadcn/ui and uses its token sheet.

1. Re-vendor / rebuild with the Alder release that carries alder-ui `v0.4.0`.
2. Replace every old token in your own CSS: `--al-radius-*` to `--radius-sm|md|lg|xl`;
   `--al-font-mono` / `--al-font-sans` to `--font-mono` / `--font-sans`;
   `--al-destructive-text` to `--destructive`; `--al-primary` and the other plain colour
   tokens to the shadcn name without the prefix; `--al-shadow-sm` to `--shadow-sm`;
   `--al-space-*`, `--al-text-*`, `--al-leading*`, `--al-weight-*`, `--al-control-h-*`,
   `--al-ring-*` to literal rem values or Tailwind-scale equivalents; `--al-*-soft` and
   `--al-*-border` have no replacement (alerts no longer use them). Only
   `--al-width-narrow|normal|wide` survive.
   `grep -rn -e '--al-' static/ src/ | grep -v -e '--al-width-'` finds the rest.
3. Dark mode: add the theme script to the `<head>` of your Layout, before the stylesheet
   link (the exact line is under "Light and dark" above). The CSS-only
   OS-dark block and `[data-theme="dark"]` are gone; `.dark` on `<html>` is the only switch.
4. Rebuild, look at each page in light and dark, and delete any app CSS that fought the
   old look.

Fonts: `al.css` loads Geist and Geist Mono from `fonts/` beside it; copy `fonts/` with `al.css`.

### Token replacements

| removed | replacement |
|---|---|
| `--al-radius-sm` / `--al-radius-full` | `--radius-sm` (6px at default `--radius`) / literal `9999px` |
| `--radius` (was 0.5rem) | `--radius` (now 0.625rem); also `--radius-md`, `--radius-lg`, `--radius-xl` |
| `--al-font-sans` / `--al-font-mono` | `--font-sans` / `--font-mono` |
| `--al-destructive-text` | `--destructive` |
| `--al-shadow-sm` | `--shadow-sm` (also new: `--shadow-xs`, `--shadow-md`, `--shadow-lg`) |
| `--al-space-0-5 … -10` | literal `0.125rem 0.25rem 0.375rem 0.5rem 0.75rem 1rem 1.5rem 2rem 2.5rem` |
| `--al-text-xs/sm/base/lg` | literal `0.75rem / 0.875rem / 1rem / 1.125rem` |
| `--al-leading` / `--al-leading-tight` | literal `1.5` / `1.25` |
| `--al-weight-normal/medium/semibold` | literal `400 / 500 / 600` |
| `--al-control-h-sm/md/lg` | literal `2rem / 2.25rem / 2.5rem` (shadcn h-8/h-9/h-10) |
| `--al-checkbox-size`, `--al-border-width` | literal `1rem`, `1px` |
| `--al-ring-width`, `--al-ring-offset` | none: the focus ring is `0 0 0 3px color-mix(in oklab, var(--ring) 50%, transparent)` |
| `--al-disabled-opacity`, `--al-duration` | literal `0.5`, `150ms` |
| `--al-{info,success,warning,destructive}-soft[-foreground]`, `--al-*-border` | no replacement (alerts use `--card`, `--card-foreground`, `--border`, `--destructive`) |
| `--al-width-narrow/normal/wide` | **kept** |

## Tests

```sh
python3 test/check.py          # all checks
python3 -m unittest discover -s test -p 'test_*.py'  # unit tests
python3 test/parity.py --strict  # parity with shadcn/ui (needs the dev venv, see below)
python3 test/check.py --table  # and print the contrast table
python3 scripts/build.py       # rebuild al.css after editing tokens or components
```

Python 3 with the standard library only; no Node. The checks: the manifest
keeps its published API; every selector names a declared element, attribute,
value and slot, and everything declared is styled; no hard-coded colours or
font families in components, base or typography (lengths are literal, as in
Tailwind); all motion sits under `prefers-reduced-motion: no-preference`; the light and dark token sets are complete;
the contrast ratios computed from the token values pass AA; the demos use only
declared attributes and slots and show every variant; `al.css` is up to date.
CI runs `check.py` in its own job and the unit tests and parity in the `parity` job.

### Parity with shadcn/ui

`test/parity.py` compares alder-ui against shadcn/ui: it loads the committed
reference grid (`ref/dist/index.html`, see `ref/README.md`) and its twin
(`demo/parity.html`, the same grid in the markup Alder emits) in headless
Chromium, light and dark, and diffs every marked element's computed style
(colour, border, radius, shadow, type, padding, size, gap, opacity, outline) at
rest and on hover and keyboard focus. It needs Playwright for Python and
Pillow, as dev dependencies only (no Node):

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m playwright install chromium

.venv/bin/python -m unittest discover -s test -p 'test_*.py'  # unit tests, no browser
.venv/bin/python test/parity.py                   # the gate: a diff table per component
.venv/bin/python test/parity.py --only button     # one component
.venv/bin/python test/parity.py --shots           # also ref | alder-ui | diff PNGs in ref/out/
.venv/bin/python test/parity.py --strict          # also fail while any component is pending
```

It fails on any difference in a component that is not listed as `pending` in
`test/parity-allow.json` and not allowed there; every allow entry carries a
one-line reason. Structural gaps (a label wrapping the input, a native
checkbox) may be allowed; colour, spacing, radius, type and shadow values must
match, except the standing deviations listed there.
CI runs the unit tests and the gate in the `parity` job and uploads
the screenshots as the `triptychs` artifact.

## License

Apache-2.0. Copyright 2026 Tavish Pegram. See [LICENSE](LICENSE).

## The interactive tier (v0.4.0)

`al-dialog`, `al-popover`, `al-menu`, `al-tabs` (with `al-tab`, `al-panel`),
`al-toast` (with the `al-toasts` region), `al-tooltip` and `al-devpanel` are
built on the platform's `<dialog>`, popover, invoker commands (`commandfor` /
`command`) and CSS anchor positioning. Each demo shows the no-JavaScript form
first (`<!-- no-js -->`), then the enhanced states.

`al-dialog` wraps a native `<dialog>` that **the author writes**: Alder's
renderer writes it for you (the `id`, the `<h2 slot="header">`, the close
`<form method="dialog">`, `aria-labelledby`); other stacks write it by hand, as
`demo/dialog.html` does. The stylesheet styles both the bare `al-dialog > dialog`
and the markup Alder emits, and `test/check.py` checks that the demo's
dismissible dialog has the renderer's shape.

`al-tabs.js` builds the tabs ARIA pattern: a `<div role="tablist">` of
`<button role="tab">` (with `aria-selected`, `aria-controls` and a roving
`tabindex`) made from the labels' text and inserted before the panels, the radio
labels hidden, `role=tabpanel` with `id` and `aria-labelledby` on each panel.
Click and the arrow keys, Home and End check the (hidden) radio, so the CSS and
`al-select` work as before. With no script nothing changes: radios and labels. `variant=line` applies to those labels too (a transparent checked label with the same underline), but the muted pill does not: the labels and panels share one flex row, so nothing wraps only the labels. `al-devpanel.js` hides the sections that are not
selected and re-applies the selection after any DOM patch (a MutationObserver),
so a server that patches the panel's inner content need not render `hidden`.

`al.js` is the bundle of the scripts (an ES module that imports nothing; build
it with `python3 scripts/build.py`): `<script type="module" src="al.js">`.
Every script (`al-tabs.js`, `al-devpanel.js`, ...) is at most 60 lines and optional: dialogs open with
`popovertarget`/`#id` links, tabs are a radio group, and a menu is a popover of
links without it. `al-shim.js` polyfills `command` / `commandfor`
(`show-modal`, `close`, `toggle-popover`, `show-popover`, `hide-popover`) and
re-announces closing as `al-close`, and makes `anchor=` on `al-popover` and
`al-menu` work (Chromium ignores the HTML attribute); `al-tooltip.js` shows
tooltips on hover and focus, whether or not `popover="hint"` exists.

Browser support: invoker commands, `popover="hint"` and CSS anchor
positioning need Chromium 135+, Safari 26 or Firefox 140. The shim covers
invoker commands on older browsers that have `<dialog>` and popover. Without
anchor positioning a popover, menu or tooltip appears at the browser's default
popover position (usable, not anchored). `anchor=` needs al.js; without it
the invoker is the anchor. Events: `al-close` (dialog, popover,
menu, toasts) and `al-select` (menu, tabs).
