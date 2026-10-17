// Optional enhancement for <al-tabs>. With no script the radio group selects.
// This adds the tabs ARIA pattern: a <div role="tablist"> of <button role="tab">
// (aria-selected, aria-controls, roving tabindex) built from the labels' text and
// put before the panels (the radio labels are hidden; the radios stay and drive
// the CSS), role="tabpanel" + id + aria-labelledby on each panel, click/arrows/
// Home/End, `selected`, <al-tab name>, and al-select (detail.tab). Load as a module.
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
  connectedCallback() {
    if (this.list) return;
    const n = ++seq, list = (this.list = document.createElement("div"));
    list.setAttribute("role", "tablist");
    this.rs = [];
    this.querySelectorAll(":scope > al-tab").forEach((tab, i) => {
      const radio = tab.querySelector("input[type=radio]"), panel = tab.querySelector(":scope > al-panel");
      if (!radio) return;
      if (!radio.name && tab.getAttribute("name")) radio.name = tab.getAttribute("name");
      if (tab.hasAttribute("selected")) radio.checked = true;
      const b = list.appendChild(document.createElement("button")), label = radio.closest("label");
      Object.assign(b, { type: "button", id: `al-tabs-${n}-${i}`, textContent: label.textContent.trim() });
      b.setAttribute("role", "tab");
      label.hidden = true;
      if (panel) {
        panel.id ||= `${b.id}-panel`;
        panel.setAttribute("role", "tabpanel");
        panel.setAttribute("aria-labelledby", b.id);
        b.setAttribute("aria-controls", panel.id);
      }
      this.rs.push(radio);
    });
    this.prepend(list);
    this.sync();
    list.addEventListener("click", (e) => {
      const i = [...list.children].indexOf(e.target.closest("button"));
      if (i >= 0) this.pick(i);
    });
    list.addEventListener("keydown", (e) => {
      const i = [...list.children].indexOf(e.target), last = this.rs.length - 1;
      const to = { ArrowRight: i < last ? i + 1 : 0, ArrowLeft: i > 0 ? i - 1 : last, Home: 0, End: last }[e.key];
      if (to === undefined || i < 0) return;
      e.preventDefault(), this.pick(to);
    });
    this.addEventListener("change", (e) => {
      this.sync();
      const tab = e.target.closest("al-tab");
      if (tab) this.dispatchEvent(new CustomEvent("al-select", { bubbles: true, detail: { tab } }));
    });
  }
});
