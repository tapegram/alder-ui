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
