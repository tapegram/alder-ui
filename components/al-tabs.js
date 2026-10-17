// Optional enhancement for <al-tabs>. With no script the radio group selects.
// This adds the tabs ARIA pattern: a <div role="tablist"> of <button role="tab">
// (aria-selected, aria-controls, roving tabindex) built from the labels' text and
// put before the panels (the radio labels are hidden; the radios stay and drive
// the CSS), role="tabpanel" + id + aria-labelledby on each panel, click/arrows/
// `selected`, <al-tab name>, and al-select (detail.tab); al-tabs-keys.js adds the click
// and the arrow keys. A MutationObserver
// rebuilds all of it, and the chosen tab, after a DOM patch (a morph) undoes it.
let seq = 0;
customElements.get("al-tabs") || customElements.define("al-tabs", class extends HTMLElement {
  sync() {
    this.rs.forEach((r, i) => {
      this.list.children[i].setAttribute("aria-selected", String(r.checked));
      this.list.children[i].tabIndex = r.checked ? 0 : -1;
    });
  }
  pick(i) {
    this.rs[i].checked = true;
    this.rs[i].dispatchEvent(new Event("change", { bubbles: true }));
    this.list.children[i].focus();
  }
  build() {
    const tabs = [...this.querySelectorAll(":scope > al-tab")].filter((t) => t.querySelector("input[type=radio]"));
    const labels = tabs.map((t) => t.querySelector("input[type=radio]").closest("label"));
    const panels = tabs.map((t) => t.querySelector(":scope > al-panel"));
    if (this.list?.parentNode === this && labels.every((l) => l.hidden) && panels.every((p) => !p || p.id)) return;
    const first = !this.list, list = document.createElement("div");
    list.setAttribute("role", "tablist");
    this.rs = tabs.map((tab) => tab.querySelector("input[type=radio]"));
    this.rs.forEach((radio, i) => {
      const tab = tabs[i], panel = panels[i], b = list.appendChild(document.createElement("button"));
      if (!radio.name && tab.getAttribute("name")) radio.name = tab.getAttribute("name");
      if (first ? tab.hasAttribute("selected") : this.at === i) radio.checked = true;
      Object.assign(b, { type: "button", id: `al-tabs-${this.n}-${i}`, textContent: labels[i].textContent.trim() });
      b.setAttribute("role", "tab");
      labels[i].hidden = true;
      if (!panel) return;
      panel.id ||= `${b.id}-panel`;
      panel.setAttribute("role", "tabpanel");
      panel.setAttribute("aria-labelledby", b.id);
      b.setAttribute("aria-controls", panel.id);
    });
    this.list?.remove();
    this.prepend((this.list = list));
    this.sync();
  }
  connectedCallback() {
    if (this.n) return;
    this.n = ++seq;
    this.build();
    this.at = this.rs.findIndex((r) => r.checked);
    new MutationObserver(() => this.build()).observe(this, { childList: true, subtree: true, attributes: true, attributeFilter: ["hidden", "id"] });
    this.addEventListener("change", (e) => {
      this.at = this.rs.indexOf(e.target);
      this.sync();
      const tab = e.target.closest("al-tab");
      if (tab) this.dispatchEvent(new CustomEvent("al-select", { bubbles: true, detail: { tab } }));
    });
  }
});
