# alder-ui

A light-DOM, token-based web-component design system. You link one
stylesheet and write elements like `<al-button>` and `<al-card>` in plain
HTML; there is no shadow DOM, no build step, and no JavaScript required.
This first tier is CSS only.

alder-ui is the built-in design system of the
[Alder](https://github.com/tapegram/alder) language, which vendors it at a
tag. It works from any stack that can write HTML.

**The full documentation is the Alder book's chapter
["The alder-ui design system"](https://github.com/tapegram/alder/blob/main/book/07-design-system.md)**
(`book/07-design-system.md` in [github.com/tapegram/alder](https://github.com/tapegram/alder)):
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
(`https://raw.githubusercontent.com/tapegram/alder-ui/v0.1.1/al.css`). Open
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
- **The input elements** wrap a real `<label>` around the control, then a
  `<ul class="errors">` list (shown in the destructive colour). `invalid`
  colours the border (on `al-checkbox`, an outline round the box); `help` is
  drawn from the attribute under the control. The `label` attribute is not
  drawn: the `<label>` is. `disabled` dims the whole field once.
- **`al-alert`**: write `role="alert"` (warning, destructive) or
  `role="status"` (info, success) yourself. `dismissible` makes room for a
  close button that the optional module `components/al-alert.js` adds
  (`<script type="module" src="al-alert.js">`; `al.css` does not load it).
  A DOM morph (Datastar, htmx, Turbo) that replaces the alert's children
  removes the added button; Alder renders its own dismiss control instead.
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
