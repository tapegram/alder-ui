// Optional enhancement for <al-menu popover id="…">: role="menu" and
// "menuitem", roving focus with the arrow keys, Home and End, focus on the
// first item when it opens, and closing on select. Fires al-select
// (detail.item) when an item is chosen. Load with <script type="module">.
customElements.get("al-menu") || customElements.define("al-menu", class extends HTMLElement {
  items() {
    return [...this.querySelectorAll(":scope > a, :scope > button")].filter((i) => i.getAttribute("aria-disabled") !== "true" && !i.disabled);
  }
  connectedCallback() {
    this.setAttribute("role", "menu");
    for (const i of this.querySelectorAll(":scope > a, :scope > button")) {
      i.setAttribute("role", "menuitem");
      i.tabIndex = -1;
    }
    this.addEventListener("toggle", (e) => e.newState === "open" && this.items()[0]?.focus());
    this.addEventListener("keydown", (e) => {
      const items = this.items(), at = items.indexOf(document.activeElement);
      const to = { ArrowDown: at + 1, ArrowUp: at - 1, Home: 0, End: items.length - 1 }[e.key];
      if (to === undefined) return;
      e.preventDefault();
      items[(to + items.length) % items.length]?.focus();
    });
    this.addEventListener("click", (e) => {
      const item = e.target.closest('[role="menuitem"]');
      if (!item || !this.contains(item)) return;
      this.dispatchEvent(new CustomEvent("al-select", { bubbles: true, detail: { item } }));
      this.hidePopover();
    });
  }
});
