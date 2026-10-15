// Optional enhancement for <al-tabs>. The radio group already gives selection
// and arrow keys with no script; this adds Home/End, the `selected` attribute
// (the server's pick), the group name from <al-tab name>, role="tabpanel",
// and the al-select event (detail.tab). Load with <script type="module">.
customElements.get("al-tabs") || customElements.define("al-tabs", class extends HTMLElement {
  radios() {
    return [...this.querySelectorAll(":scope > al-tab > label > input[type=radio]")];
  }
  connectedCallback() {
    for (const tab of this.querySelectorAll(":scope > al-tab")) {
      const radio = tab.querySelector("input[type=radio]");
      if (radio && !radio.name && tab.getAttribute("name")) radio.name = tab.getAttribute("name");
      if (radio && tab.hasAttribute("selected")) radio.checked = true;
      tab.querySelector(":scope > al-panel")?.setAttribute("role", "tabpanel");
    }
    this.addEventListener("keydown", (e) => {
      const rs = this.radios(), to = { Home: 0, End: rs.length - 1 }[e.key];
      if (to === undefined || !rs[to]) return;
      e.preventDefault();
      rs[to].checked = true;
      rs[to].focus();
      rs[to].dispatchEvent(new Event("change", { bubbles: true }));
    });
    this.addEventListener("change", (e) => {
      const tab = e.target.closest("al-tab");
      if (tab) this.dispatchEvent(new CustomEvent("al-select", { bubbles: true, detail: { tab } }));
    });
  }
});

// <al-devpanel>: a <nav> of buttons (aria-controls="<section id>") switches its
// <section>s; a button opens the panel, the selected one closes it again.
customElements.get("al-devpanel") || customElements.define("al-devpanel", class extends HTMLElement {
  connectedCallback() {
    const buttons = [...this.querySelectorAll(":scope > nav > button")];
    const show = (b) => {
      for (const x of buttons) x.setAttribute("aria-selected", String(x === b));
      for (const s of this.querySelectorAll(":scope > section")) s.hidden = s.id !== b.getAttribute("aria-controls");
    };
    if (buttons[0]) show(buttons[0]);
    this.addEventListener("click", (e) => {
      const b = e.target.closest("nav > button");
      if (!b || !buttons.includes(b)) return;
      const close = this.hasAttribute("open") && b.getAttribute("aria-selected") === "true";
      show(b);
      this.toggleAttribute("open", !close);
    });
  }
});
