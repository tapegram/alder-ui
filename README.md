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
`@layer al`). Copy it from a tagged release. Once this repository is public,
you can also link the raw file at a tag
(`https://raw.githubusercontent.com/tapegram/alder-ui/v0.3.2/al.css`). Open
`demo/index.html` to see every element, variant and state in both themes.

## Elements

The attributes are the API; [`custom-elements.json`](custom-elements.json) (a
[Custom Elements Manifest](https://github.com/webcomponents/custom-elements-manifest))
declares each one with its type, default and description.

| element | attributes | slots |
|---|---|---|
| `al-button` | `variant` (`primary` default, `secondary`, `outline`, `ghost`, `destructive`), `size` (`sm`, `md` default, `lg`), `disabled`, `type` (`button`, `submit`) | default |
| `al-input` | `label`, `placeholder`, `disabled`, `invalid`, `help` | |
| `al-textarea` | `label`, `placeholder`, `disabled`, `invalid`, `help` | |
| `al-select` | `label`, `disabled`, `invalid`, `help` | |
| `al-checkbox` | `label`, `disabled`, `invalid`, `help` | |
| `al-table` | `striped`, `dense` | default (a `<table>`) |
| `al-card` | | `header`, default, `footer`, `actions` |
| `al-badge` | `variant` (`default` default, `secondary`, `outline`, `destructive`) | default |
| `al-alert` | `variant` (`info` default, `success`, `warning`, `destructive`), `heading`, `dismissible` | default |
| `al-pagination` | `page`, `pages` | `prev`, default, `next` |
| `al-dialog` | `heading`, `size` (`sm`, `md` default, `lg`), `dismissible` | `header`, default, `actions` |
| `al-popover` | `placement` (`top`, `bottom` default, `left`, `right`), `offset` (`sm` default, `md`, `lg`), `anchor` | default |
| `al-menu` | | default (links or buttons) |
| `al-tabs` | | default (`al-tab`s) |
| `al-tab` | `name`, `selected` | default (a `<label>` with a radio, then an `al-panel`) |
| `al-panel` | | default |
| `al-toast` | `variant` (`info` default, `success`, `warning`, `destructive`), `timeout` (ms; default 5000, 0 = sticky) | default |
| `al-toasts` | `position` (`top-left`, `top-right`, `bottom-left`, `bottom-right` default) | default (`al-toast`s) |
| `al-tooltip` | `for` | default (text) |
| `al-devpanel` | `open` | default (a `<nav>` of buttons, then `<section>`s) |
| `al-stack` | `gap` (`sm`, `md` default, `lg`), `direction` (`column` default, `row`) | default |
| `al-page` | `width` (`narrow`, `normal` default, `wide`) | default |

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
  `var(--…)` from [`tokens.css`](tokens.css). Colours use shadcn/ui's names
  (`--background`, `--foreground`, `--primary`, `--primary-foreground`,
  `--secondary`, `--muted`, `--accent`, `--destructive`, `--border`,
  `--input`, `--ring`, `--radius`, …); alder-ui's own tokens start with
  `--al-`.
- **Overriding.** `al.css` puts everything in `@layer al`, so your own
  unlayered CSS always wins, whatever its specificity. Set a token on
  `:root { --primary: …; }` to change it in both themes. To change only the
  dark theme, set it in `[data-theme="dark"] { … }`, and for the OS-driven
  dark theme also in
  `@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { … } }`.
- **Light and dark.** Dark follows `prefers-color-scheme`; set
  `data-theme="light"` or `data-theme="dark"` on `<html>` (or any subtree) to
  force one.
- **View transitions.** `tokens.css` opts every page into cross-document
  view transitions (`@view-transition { navigation: auto }`), so a
  same-origin navigation cross-fades instead of flashing a blank frame
  (white, even in the dark theme). Browsers without them ignore it.
- **No JavaScript required.** Every element works server-rendered; scripts
  are optional enhancements only.
- **Attributes are the API**; class names, where any are needed, start with
  `al-`.
- **Accessible by default.** Real labels, visible `:focus-visible` rings in
  `--ring`, and WCAG AA contrast for every variant in both themes.

## Tests

```sh
python3 test/check.py          # all checks
python3 test/check.py --table  # and print the contrast table
python3 scripts/build.py       # rebuild al.css after editing tokens or components
```

Python 3 with the standard library only; no Node. The checks: the manifest
keeps its published API; every selector names a declared element, attribute,
value and slot, and everything declared is styled; no hard-coded colours,
lengths or fonts in components; the light and dark token sets are complete;
the contrast ratios computed from the token values pass AA; the demos use only
declared attributes and slots and show every variant; `al.css` is up to date.
CI runs the same script.

## License

Apache-2.0. Copyright 2026 Tavish Pegram. See [LICENSE](LICENSE).

## The interactive tier (v0.3.2)

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
`al-select` work as before. With no script nothing changes: radios and labels. `al-devpanel.js` hides the sections that are not
selected and re-applies the selection after any DOM patch (a MutationObserver),
so a server that patches the panel's inner content need not render `hidden`.

`al.js` is the bundle of the scripts (an ES module that imports nothing; build
it with `python3 scripts/build.py`): `<script type="module" src="al.js">`.
Every script (`al-tabs.js`, `al-devpanel.js`, ...) is at most 60 lines and optional: dialogs open with
`popovertarget`/`#id` links, tabs are a radio group, and a menu is a popover of
links without it. `al-shim.js` polyfills `command` / `commandfor`
(`show-modal`, `close`, `toggle-popover`, `show-popover`, `hide-popover`) and
re-announces closing as `al-close`; `al-tooltip.js` shows tooltips on hover and
focus, whether or not `popover="hint"` exists.

Browser support: invoker commands, `popover="hint"` and CSS anchor
positioning need Chromium 135+, Safari 26 or Firefox 140. The shim covers
invoker commands on older browsers that have `<dialog>` and popover. Without
anchor positioning a popover, menu or tooltip appears at the browser's default
popover position (usable, not anchored). Events: `al-close` (dialog, popover,
menu, toasts) and `al-select` (menu, tabs).
