// <al-devpanel>: a <nav> of buttons (aria-controls="<section id>") switches its
// <section>s; a button opens the panel, the selected one closes it again. The
// script hides the sections that are not selected and re-applies the selection
// after any DOM patch (a MutationObserver), so a server that patches the
// panel's inner content need not render `hidden` or `aria-selected`.
customElements.get("al-devpanel") || customElements.define("al-devpanel", class extends HTMLElement {
  buttons() {
    return [...this.querySelectorAll(":scope > nav > button")];
  }
  apply() {
    const bs = this.buttons(), b = bs.find((x) => x.getAttribute("aria-controls") === this.sel) || bs[0];
    if (!b) return;
    this.sel = b.getAttribute("aria-controls");
    for (const x of bs) if (x.getAttribute("aria-selected") !== String(x === b)) x.setAttribute("aria-selected", String(x === b));
    for (const s of this.querySelectorAll(":scope > section")) if (s.hidden !== (s.id !== this.sel)) s.hidden = s.id !== this.sel;
  }
  connectedCallback() {
    this.sel = this.buttons().find((x) => x.getAttribute("aria-selected") === "true")?.getAttribute("aria-controls");
    this.apply();
    new MutationObserver(() => this.apply()).observe(this, {
      childList: true, subtree: true, attributes: true, attributeFilter: ["hidden", "aria-selected"],
    });
    this.addEventListener("click", (e) => {
      const b = e.target.closest("nav > button");
      if (!b || !this.buttons().includes(b)) return;
      const close = this.hasAttribute("open") && b.getAttribute("aria-selected") === "true";
      this.sel = b.getAttribute("aria-controls");
      this.apply();
      this.toggleAttribute("open", !close);
    });
  }
});
