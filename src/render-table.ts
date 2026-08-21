import { isEuCountry } from "./eu-countries";
import type { ResultRow } from "./types";

function escapeHtml(value: string): string {
  const div = document.createElement("div");
  div.textContent = value;
  return div.innerHTML;
}

export function renderResultsTable(container: HTMLElement, rows: ResultRow[]): void {
  const body = rows
    .map(
      (r) => `
        <tr>
          <td>${escapeHtml(r.hostname)}</td>
          <td>${escapeHtml(r.orgName ?? "onbekend")}</td>
          <td>${escapeHtml(r.orgCountry ?? "onbekend")}</td>
          <td>${isEuCountry(r.orgCountry) ? "✓ EU" : "buiten EU"}</td>
          <td>${r.count}</td>
        </tr>`
    )
    .join("");

  container.innerHTML = `
    <table class="results-table">
      <thead>
        <tr>
          <th>Hostname</th>
          <th>Leverancier</th>
          <th>Statutaire zetel</th>
          <th>EU?</th>
          <th>Aantal requests</th>
        </tr>
      </thead>
      <tbody>${body}</tbody>
    </table>`;
}
