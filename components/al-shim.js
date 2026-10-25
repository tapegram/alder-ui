// Polyfills for browsers without invoker commands (Chromium < 135, Safari < 26,
// Firefox < 140): <button commandfor="id" command="show-modal | close |
// toggle-popover | show-popover | hide-popover"> works as the platform's.
// Also re-announces closing as the bubbling al-close event on al-dialog,
// al-popover and al-menu, and makes anchor="<id>" on al-popover / al-menu
// work (Chromium ignores the HTML attribute). (popover="hint" needs no shim:
// al-tooltip.js shows and hides its tooltip on hover and focus, so an older
// browser treating "hint" as "manual" behaves the same.)
if (!("commandForElement" in HTMLButtonElement.prototype)) {
  document.addEventListener("click", (e) => {
    const b = e.target.closest("button[commandfor]");
    const t = b && !b.disabled && document.getElementById(b.getAttribute("commandfor"));
    if (!t) return;
    const c = b.getAttribute("command");
    if (c === "show-modal" && !t.open) t.showModal();
    else if (c === "close") t.close();
    else if (c === "toggle-popover") t.togglePopover();
    else if (c === "show-popover") t.showPopover();
    else if (c === "hide-popover") t.hidePopover();
  });
}
const closed = (e, sel) => {
  const host = e.target.closest && e.target.closest(sel);
  if (host) host.dispatchEvent(new CustomEvent("al-close", { bubbles: true }));
};
document.addEventListener("close", (e) => closed(e, "al-dialog"), true);
document.addEventListener("toggle", (e) => e.newState === "closed" && closed(e, "al-popover, al-menu"), true);
// anchor="<id>": at every open the named element gets a generated anchor-name,
// after any of its own, and the popover the same position-anchor. An id that
// names nothing leaves the invoker as the implicit anchor. Names are generated
// (ids need not be valid dashed-idents) and kept per element.
const names = new WeakMap();
let seq = 0;
document.addEventListener("beforetoggle", (e) => {
  const p = e.target;
  if (e.newState !== "open" || !p.matches || !p.matches("al-popover, al-menu")) return;
  const a = p.hasAttribute("anchor") && document.getElementById(p.getAttribute("anchor"));
  const ours = p.style.getPropertyValue("position-anchor").startsWith("--al-anchor-");
  if (!a) return ours && p.style.removeProperty("position-anchor");
  if (!names.has(a)) names.set(a, "--al-anchor-" + ++seq);
  const n = names.get(a), own = a.style.getPropertyValue("anchor-name");
  const list = own && own !== "none" ? own.split(",").map((s) => s.trim()) : [];
  if (!list.includes(n)) a.style.setProperty("anchor-name", list.concat(n).join(", "));
  p.style.setProperty("position-anchor", n);
}, true);
