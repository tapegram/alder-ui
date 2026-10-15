// Optional enhancement for <al-toast> inside <al-toasts popover="manual">:
// shows the region when a toast connects, sets role="status", closes the toast
// after `timeout` ms (default 5000; 0 keeps it) and hides an empty region.
// Fires al-close on the region when a toast closes. Load with <script type="module">.
customElements.get("al-toast") || customElements.define("al-toast", class extends HTMLElement {
  connectedCallback() {
    this.hasAttribute("role") || this.setAttribute("role", "status");
    const region = this.closest("al-toasts");
    if (region && region.hasAttribute("popover") && !region.matches(":popover-open")) region.showPopover();
    const ms = this.hasAttribute("timeout") ? Number(this.getAttribute("timeout")) : 5000;
    if (ms > 0) this.timer = setTimeout(() => this.close(), ms);
  }
  disconnectedCallback() {
    clearTimeout(this.timer);
  }
  close() {
    const region = this.closest("al-toasts");
    this.remove();
    if (!region) return;
    region.dispatchEvent(new CustomEvent("al-close", { bubbles: true, detail: { toast: this } }));
    if (!region.querySelector("al-toast") && region.matches(":popover-open")) region.hidePopover();
  }
});
