import { escapeHtml } from "./render-table";

/** Renders detected browser-extension IDs for local display only. These
 * are never sent to the lookup backend — an extension ID has no
 * ASN/PeeringDB entry, and forwarding it would leak which specific
 * extension the visitor has installed. */
export function renderExtensionsList(
  container: HTMLElement,
  extensions: string[],
): void {
  if (extensions.length === 0) {
    container.innerHTML = "";
    return;
  }
  const items = extensions.map((id) => `<li>${escapeHtml(id)}</li>`).join("");
  container.innerHTML = `
    <h2>Browserextensies gedetecteerd (blijft lokaal, wordt niet verstuurd)</h2>
    <ul class="extensions-list">${items}</ul>`;
}
