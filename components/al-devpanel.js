// <al-devpanel>: a <nav> of buttons (aria-controls="<section id>") switches its
// <section>s; a button opens the panel, the selected one closes it again. The
// script hides the sections that are not selected and re-applies the selection
// after any DOM patch (a MutationObserver), so a server that patches the
// panel's inner content need not render `hidden` or `aria-selected`.
//
// The open panel resizes by the grip along its top edge: drag it, or focus it
// and press ArrowUp/ArrowDown (Shift for a bigger step, Home for the default).
// The height it sets is --devpanel-h / --devpanel-max, remembered in
// localStorage so it survives the next request's render.
//
// The grip is created here rather than rendered by the server, so apply() puts
// it back after a patch replaces the panel's children; its events are
// delegated from the host, so a freshly made grip needs no binding.
const DP_KEY = "al-devpanel-h";
const DP_MIN = 64; // the shortest the panel may be dragged, in px
const DP_VARS = ["--devpanel-h", "--devpanel-max"];

customElements.get("al-devpanel") || customElements.define("al-devpanel", class extends HTMLElement {
  buttons() {
    return [...this.querySelectorAll(":scope > nav > button")];
  }

  // height is the open section's height: what the grip resizes. It is undefined when the panel
  // is shut, since the section is display:none and has no box to measure.
  height() {
    return this.querySelector(":scope > section:not([hidden])")?.getBoundingClientRect().height;
  }

  // resizeTo sets that height, or clears it back to the default with null, and remembers the
  // choice. The value is clamped, so the grip can neither drag the panel shut nor past the
  // viewport.
  resizeTo(px) {
    let value = "";
    if (px != null) {
      const max = Math.max(DP_MIN, Math.round(innerHeight * 0.9));
      value = Math.min(max, Math.max(DP_MIN, Math.round(px))) + "px";
    }
    for (const name of DP_VARS) {
      if (value) this.style.setProperty(name, value);
      else this.style.removeProperty(name);
    }
    try {
      if (value) localStorage.setItem(DP_KEY, value);
      else localStorage.removeItem(DP_KEY);
    } catch (e) {
      // storage blocked or full: the height still applies to this page
    }
  }

  // drag follows the pointer. The panel sits at the bottom of the viewport, so a pointer moving
  // up makes it taller. move and up listen on the window, not the grip, so a pointer that
  // outruns the grip keeps resizing until it is released.
  drag(e) {
    const start = this.height();
    if (start == null || e.button !== 0) return;
    e.preventDefault();
    const from = e.clientY;
    const move = (ev) => this.resizeTo(start + (from - ev.clientY));
    const up = () => {
      removeEventListener("pointermove", move);
      removeEventListener("pointerup", up);
    };
    addEventListener("pointermove", move);
    addEventListener("pointerup", up);
  }

  // key is the keyboard equivalent of dragging, for the focused grip.
  key(e) {
    const step = e.shiftKey ? 64 : 16;
    if (e.key === "ArrowUp") this.resizeTo(this.height() + step);
    else if (e.key === "ArrowDown") this.resizeTo(this.height() - step);
    else if (e.key === "Home") this.resizeTo(null);
    else return;
    e.preventDefault();
  }

  grip() {
    let g = this.querySelector(":scope > [data-grip]");
    if (!g) {
      g = document.createElement("div");
      g.tabIndex = 0;
      g.setAttribute("data-grip", "");
      g.setAttribute("role", "separator");
      g.setAttribute("aria-label", "Resize the developer panel");
    }
    // the grip is the panel's top edge, wherever the server put the rest of the children
    if (this.firstChild !== g) this.prepend(g);
  }

  apply() {
    const bs = this.buttons(), b = bs.find((x) => x.getAttribute("aria-controls") === this.sel) || bs[0];
    if (!b) return;
    this.sel = b.getAttribute("aria-controls");
    for (const x of bs) if (x.getAttribute("aria-selected") !== String(x === b)) x.setAttribute("aria-selected", String(x === b));
    for (const s of this.querySelectorAll(":scope > section")) if (s.hidden !== (s.id !== this.sel)) s.hidden = s.id !== this.sel;
    this.grip();
  }

  // restore re-applies the remembered height before the first paint.
  restore() {
    try {
      const v = localStorage.getItem(DP_KEY);
      if (v) for (const name of DP_VARS) this.style.setProperty(name, v);
    } catch (e) {
      // storage blocked: the default height applies
    }
  }

  connectedCallback() {
    this.sel = this.buttons().find((x) => x.getAttribute("aria-selected") === "true")?.getAttribute("aria-controls");
    this.restore();
    this.apply();
    new MutationObserver(() => this.apply()).observe(this, {
      childList: true, subtree: true, attributes: true, attributeFilter: ["hidden", "aria-selected"],
    });
    this.addEventListener("pointerdown", (e) => {
      if (e.target.closest("[data-grip]")) this.drag(e);
    });
    this.addEventListener("keydown", (e) => {
      if (e.target.closest("[data-grip]")) this.key(e);
    });
    this.addEventListener("click", (e) => {
      const b = e.target.closest("nav > button");
      if (!b || !this.buttons().includes(b)) return;
      const close = this.hasAttribute("open") && b.getAttribute("aria-selected") === "true";
      this.sel = b.getAttribute("aria-controls");
      this.apply();
      this.toggleAttribute("open", !close);
    });
  }
});
