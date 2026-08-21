import { isEuCountry } from "./eu-countries";
import type { ResultRow } from "./types";

function escapeHtml(value: string): string {
  const div = document.createElement("div");
  div.textContent = value;
  return div.innerHTML;
}

function formatCountry(row: ResultRow): string {
  if (!row.orgCountry) return "onbekend";
  const country = escapeHtml(row.orgCountry);
  return row.orgCountrySource === "ripestat" ? `${country} (RIPE)` : country;
}

export function renderResultsTable(
  container: HTMLElement,
  rows: ResultRow[],
): void {
  const body = rows
    .map(
      (r) => `
        <tr>
          <td>${escapeHtml(r.hostname)}</td>
          <td>${escapeHtml(r.orgName ?? "onbekend")}</td>
          <td>${formatCountry(r)}</td>
          <td>${isEuCountry(r.orgCountry) ? "✓ EU" : "buiten EU"}</td>
          <td>${r.count}</td>
        </tr>`,
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
