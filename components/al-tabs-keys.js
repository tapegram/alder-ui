// Optional: the tab buttons al-tabs.js builds respond to a click and to the arrow
// keys, Home and End (each picks the tab: it checks the radio, so al-select fires).
// One listener on the document serves every <al-tabs>, rebuilt or not.
document.addEventListener("click", (e) => {
  const tabs = e.target.closest?.("al-tabs [role=tab]")?.closest("al-tabs");
  const i = tabs ? [...tabs.list.children].indexOf(e.target.closest("[role=tab]")) : -1;
  if (i >= 0) tabs.pick(i);
});
document.addEventListener("keydown", (e) => {
  const tabs = e.target.closest?.("al-tabs [role=tab]")?.closest("al-tabs");
  if (!tabs) return;
  const i = [...tabs.list.children].indexOf(e.target), last = tabs.rs.length - 1;
  const to = { ArrowRight: i < last ? i + 1 : 0, ArrowLeft: i > 0 ? i - 1 : last, Home: 0, End: last }[e.key];
  if (to === undefined) return;
  e.preventDefault();
  tabs.pick(to);
});
