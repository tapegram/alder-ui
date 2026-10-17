// Optional enhancement for <al-tabs>. The radio group already gives selection
// and arrow keys with no script; this adds the tabs ARIA pattern (role=tablist
// on <al-tabs>, role=tab on each radio with aria-selected, aria-controls and a
// roving tabindex, role=tabpanel with id and aria-labelledby on each panel),
// Home/End, the `selected` attribute, the group name from <al-tab name>, and
// the al-select event (detail.tab). Load with <script type="module">.
let seq = 0;
customElements.get("al-tabs") || customElements.define("al-tabs", class extends HTMLElement {
  radios() {
    return [...this.querySelectorAll(":scope > al-tab > label > input[type=radio]")];
  }
  sync() {
    for (const r of this.radios()) {
      r.setAttribute("aria-selected", String(r.checked));
      r.tabIndex = r.checked ? 0 : -1;
    }
  }
  connectedCallback() {
    const n = ++seq;
    this.setAttribute("role", "tablist");
    [...this.querySelectorAll(":scope > al-tab")].forEach((tab, i) => {
      const radio = tab.querySelector("input[type=radio]"), panel = tab.querySelector(":scope > al-panel");
      tab.setAttribute("role", "none");
      if (!radio) return;
      if (!radio.name && tab.getAttribute("name")) radio.name = tab.getAttribute("name");
      if (tab.hasAttribute("selected")) radio.checked = true;
      radio.id ||= `al-tabs-${n}-${i}-tab`;
      radio.setAttribute("role", "tab");
      if (!panel) return;
      panel.id ||= `al-tabs-${n}-${i}-panel`;
      panel.setAttribute("role", "tabpanel");
      panel.setAttribute("aria-labelledby", radio.id);
      radio.setAttribute("aria-controls", panel.id);
    });
    this.sync();
    this.addEventListener("keydown", (e) => {
      const rs = this.radios(), to = { Home: 0, End: rs.length - 1 }[e.key];
      if (to === undefined || !rs[to]) return;
      e.preventDefault();
      rs[to].checked = true;
      rs[to].focus();
      rs[to].dispatchEvent(new Event("change", { bubbles: true }));
    });
    this.addEventListener("change", (e) => {
      this.sync();
      const tab = e.target.closest("al-tab");
      if (tab) this.dispatchEvent(new CustomEvent("al-select", { bubbles: true, detail: { tab } }));
    });
  }
});
