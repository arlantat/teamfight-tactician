/** Keyboard-navigable search over catalog entries for choosing filters. */
import { el, button, picture } from "./dom.js";

/** Search box with a keyboard-navigable result list. */
export function picker(lookup, { placeholder, kinds, onPick, autofocus }) {
  const wrap = el("div", "explorer-picker");
  const input = el("input");
  input.type = "search";
  input.placeholder = placeholder;
  input.autocomplete = "off";
  input.setAttribute("aria-label", placeholder);
  input.setAttribute("role", "combobox");
  input.setAttribute("aria-expanded", "false");
  const list = el("div", "explorer-picker-list");
  list.setAttribute("role", "listbox");
  let options = [];
  let active = 0;
  const close = () => {
    list.replaceChildren();
    input.setAttribute("aria-expanded", "false");
  };
  const choose = (option) => {
    input.value = "";
    close();
    onPick(option);
  };
  const render = () => {
    const term = input.value;
    options = lookup.search(
      term,
      kinds.filter((kind) => kind !== "level"),
    );
    if (
      kinds.includes("level") &&
      "player level".includes(term.trim().toLowerCase())
    )
      options.unshift({
        kind: "level",
        id: "level",
        name: "Player level",
        detail: "Final level",
      });
    active = Math.min(active, Math.max(0, options.length - 1));
    list.replaceChildren(
      ...options.map((option, index) => {
        const row = button(
          "",
          `explorer-option${index === active ? " active" : ""}`,
          () => choose(option),
        );
        row.setAttribute("role", "option");
        row.setAttribute("aria-selected", String(index === active));
        row.tabIndex = -1;
        row.append(
          picture(option.image, option.name, "explorer-option-icon"),
          el("strong", "", option.name),
          el(
            "small",
            "",
            `${lookup.kindLabel(option.kind)} ${option.detail ? `· ${option.detail}` : ""}`,
          ),
        );
        return row;
      }),
    );
    if (!options.length)
      list.append(el("p", "explorer-option-empty", "No matches."));
    input.setAttribute("aria-expanded", "true");
  };
  input.addEventListener("focus", render);
  input.addEventListener("input", () => {
    active = 0;
    render();
  });
  input.addEventListener("keydown", (event) => {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      active =
        (active + (event.key === "ArrowDown" ? 1 : -1) + options.length) %
        Math.max(1, options.length);
      render();
      list.querySelector(".active")?.scrollIntoView({ block: "nearest" });
    } else if (event.key === "Enter" && options[active]) {
      event.preventDefault();
      choose(options[active]);
    } else if (event.key === "Escape") {
      close();
      input.blur();
    }
  });
  wrap.addEventListener("focusout", (event) => {
    if (!wrap.contains(event.relatedTarget)) close();
  });
  wrap.append(input, list);
  if (autofocus) queueMicrotask(() => input.focus());
  return wrap;
}
