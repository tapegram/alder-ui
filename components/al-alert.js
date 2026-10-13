// Optional enhancement for <al-alert dismissible>: adds a close button that
// removes the alert. Load with <script type="module" src="al-alert.js">.
customElements.define("al-alert", class extends HTMLElement {
  connectedCallback() {
    if (!this.hasAttribute("dismissible") || this.querySelector(":scope > .al-alert-dismiss")) return;
    const b = Object.assign(document.createElement("button"), { type: "button", className: "al-alert-dismiss", textContent: "×" });
    b.setAttribute("aria-label", "Dismiss");
    b.addEventListener("click", () => this.remove());
    this.append(b);
  }
});
