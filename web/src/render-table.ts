import { isEuCountry } from "./eu-countries";
import { isKnownTracker } from "./tracker-patterns";
import type { ResultRow } from "./types";

export function escapeHtml(value: string): string {
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
    .map((r) => {
      const trackerBadge = isKnownTracker(r.hostname)
        ? ` <span class="tracker-badge" title="Komt overeen met een bekend tracking-domeinpatroon">tracker</span>`
        : "";
      return `
        <tr>
          <td>${escapeHtml(r.hostname)}${trackerBadge}</td>
          <td>${escapeHtml(r.orgName ?? "onbekend")}</td>
          <td>${formatCountry(r)}</td>
          <td>${isEuCountry(r.orgCountry) ? "✓ EU" : "buiten EU"}</td>
          <td>${r.count}</td>
          <td>${r.cookieCount > 0 ? r.cookieCount : "-"}</td>
        </tr>`;
    })
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
          <th>Cookies</th>
        </tr>
      </thead>
      <tbody>${body}</tbody>
    </table>`;
}
