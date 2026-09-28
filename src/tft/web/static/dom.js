/** Small safe DOM primitives shared by every view. */
export function el(tag, className = "", text = "") {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== "") node.textContent = String(text);
  return node;
}
export function button(text, className, action) {
  const node = el("button", className, text);
  node.type = "button";
  if (action) node.addEventListener("click", action);
  return node;
}
export function link(text, href, className = "") {
  const node = el("a", className, text);
  node.href = href;
  return node;
}
export function icon(name, className = "") {
  const paths = {
    overview:
      '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
    champions: '<path d="m5 3 7 7 7-7 2 2-7 7 7 7-2 2-7-7-7 7-2-2 7-7-7-7z"/>',
    traits:
      '<path d="m12 2 9 5v10l-9 5-9-5V7z"/><path d="m12 7 4 5-4 5-4-5z"/>',
    items: '<path d="m8 3 8 0 5 6-9 12L3 9zM3 9h18M8 3l4 18 4-18"/>',
    augments:
      '<path d="m12 2 2.5 7.5L22 12l-7.5 2.5L12 22l-2.5-7.5L2 12l7.5-2.5z"/>',
    builder:
      '<path d="m7 3 5 3v6l-5 3-5-3V6zm10 9 5 3v6l-5 3-5-3v-6zM12 6l5-3 5 3v6l-5 3M7 15v6l5 3"/>',
    arrow: '<path d="M4 12h16m-6-6 6 6-6 6"/>',
    gold: '<circle cx="12" cy="12" r="8"/><path d="M12 8v8M9 10h5l-4 4h5"/>',
    search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
    leaf: '<path d="M20 3C8 2 1 8 5 16c8 5 15-2 15-13zM4 21 16 8"/>',
    notes: '<path d="M7 3h8l4 4v14H7zM15 3v4h4M9 12h6M9 16h4"/>',
    explorer: '<path d="M3 5h18l-7 8v6l-4 2v-8z"/>',
  };
  const node = el("span", `icon ${className}`);
  node.setAttribute("aria-hidden", "true");
  node.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">${paths[name] || paths.augments}</svg>`;
  return node;
}
export function picture(url, name, className = "", eager = false) {
  const wrap = el("span", `picture ${className}`);
  const fallback = el("span", "image-fallback", name?.slice(0, 1) || "✧");
  wrap.append(fallback);
  if (url && url !== "None") {
    const image = document.createElement("img");
    image.alt = name || "";
    image.loading = eager ? "eager" : "lazy";
    image.decoding = "async";
    image.src = url;
    image.addEventListener("load", () => fallback.remove(), { once: true });
    image.addEventListener("error", () => image.remove(), { once: true });
    wrap.append(image);
  }
  return wrap;
}
export function gold(cost) {
  const node = el("span", `cost cost-${Math.min(5, cost)}`, cost);
  node.prepend(icon("gold"));
  return node;
}
export function humanize(value = "") {
  return String(value)
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}
export function description(value = "", effects = {}) {
  const variables = Object.fromEntries(
    Object.entries(effects || {}).map(([key, val]) => [key.toLowerCase(), val]),
  );
  return String(value)
    .replace(/<br\s*\/?\s*>/gi, "\n")
    .replace(/<[^>]*>/g, "")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/%i:[^%]*%/g, "")
    .replace(/\{\{[^}]+\}\}/g, "")
    .replace(/@([^@]+)@/g, (_, token) => {
      const parts = token.split("*");
      const v = variables[parts[0].toLowerCase()];
      const multiplier = parts.length === 2 ? Number(parts[1]) : 1;
      return typeof v === "number" &&
        Number.isFinite(multiplier) &&
        parts.length <= 2
        ? Number((v * multiplier).toFixed(2)).toString()
        : "◇";
    })
    .replace(/\(\s*\)/g, "")
    .replace(/[ \t]{2,}/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}
export function emptyState(title, copy, action) {
  const node = el("div", "empty-state");
  node.append(icon("leaf"), el("h3", "", title), el("p", "", copy));
  if (action) node.append(action);
  return node;
}
export function toast(message) {
  const node = document.querySelector("#toast");
  node.textContent = message;
  node.classList.add("visible");
  clearTimeout(toast.timeout);
  toast.timeout = setTimeout(() => node.classList.remove("visible"), 3200);
}
export function sectionHeading(eyebrow, title, href, action = "Explore all") {
  const head = el("div", "section-heading");
  const text = el("div");
  if (eyebrow) text.append(el("p", "eyebrow", eyebrow));
  text.append(el("h2", "", title));
  head.append(text);
  if (href) {
    const a = link(action, href, "text-link");
    a.append(icon("arrow"));
    head.append(a);
  }
  return head;
}
