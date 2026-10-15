// Optional enhancement for <al-tooltip for="id">text</al-tooltip>: makes it a
// popover="hint" (the browser treats it as "manual" where "hint" is unknown;
// the behaviour is the same), anchors it to the trigger, wires
// aria-describedby, and shows it on hover and keyboard focus; Escape hides it.
customElements.get("al-tooltip") || customElements.define("al-tooltip", class extends HTMLElement {
  connectedCallback() {
    const trigger = document.getElementById(this.getAttribute("for"));
    if (!trigger || this.wired) return;
    this.wired = true;
    this.id ||= "al-tip-" + Math.random().toString(36).slice(2, 8);
    this.hasAttribute("popover") || this.setAttribute("popover", "hint");
    this.setAttribute("role", "tooltip");
    this.setAttribute("anchor", trigger.id);
    trigger.setAttribute("aria-describedby", this.id);
    const show = () => this.matches(":popover-open") || this.showPopover();
    const hide = () => this.matches(":popover-open") && this.hidePopover();
    for (const [type, f] of [["pointerenter", show], ["focus", show], ["pointerleave", hide], ["blur", hide]]) trigger.addEventListener(type, f);
    trigger.addEventListener("keydown", (e) => e.key === "Escape" && hide());
  }
});
