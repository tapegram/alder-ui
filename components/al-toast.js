// Optional enhancement for <al-toast> inside <al-toasts popover="manual">:
// shows the region when a toast connects, sets role="status", closes the toast
// after `timeout` ms (default 5000; 0 keeps it) and hides an empty region.
// close() sets data-closing, lets the exit transition run (al-toast.css) and
// then removes the toast; with no transition running (reduced motion, or the
// toast not shown) it removes it at once. Fires al-close on the region when a
// toast closes. Load with <script type="module">.
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
    if (this.closing) return;
    this.closing = true;
    clearTimeout(this.timer);
    this.setAttribute("data-closing", "");
    const region = this.closest("al-toasts");
    const done = () => {
      this.remove();
      if (!region) return;
      region.dispatchEvent(new CustomEvent("al-close", { bubbles: true, detail: { toast: this } }));
      if (!region.querySelector("al-toast") && region.matches(":popover-open")) region.hidePopover();
    };
    // getAnimations() flushes style, so the exit transition (if any) has started;
    // a cancelled one (the toast hidden or removed meanwhile) settles too.
    const running = this.getAnimations().map((a) => a.finished);
    running.length ? Promise.allSettled(running).then(done) : done();
  }
});
