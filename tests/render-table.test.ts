import { describe, expect, it } from "vitest";
import { renderResultsTable } from "../src/render-table";
import type { ResultRow } from "../src/types";

describe("renderResultsTable", () => {
  it("renders one row per result with hostname, org, country, EU badge and count", () => {
    const container = document.createElement("div");
    const rows: ResultRow[] = [
      {
        hostname: "cdn.bluedolphin.app",
        count: 8,
        asn: 8075,
        orgName: "Microsoft Corporation",
        orgCountry: "IE",
      },
      { hostname: "unknown.example", count: 1, asn: null, orgName: null, orgCountry: null },
    ];

    renderResultsTable(container, rows);

    expect(container.querySelectorAll("tbody tr")).toHaveLength(2);
    expect(container.textContent).toContain("cdn.bluedolphin.app");
    expect(container.textContent).toContain("Microsoft Corporation");
    expect(container.textContent).toContain("✓ EU");
    expect(container.textContent).toContain("onbekend");
    expect(container.textContent).toContain("buiten EU");
    expect(container.textContent).toContain("8");
  });

  it("escapes HTML in organisation names to prevent XSS", () => {
    const container = document.createElement("div");
    const rows: ResultRow[] = [
      {
        hostname: "evil.example",
        count: 1,
        asn: 1,
        orgName: "<script>alert(1)</script>",
        orgCountry: "US",
      },
    ];

    renderResultsTable(container, rows);

    expect(container.innerHTML).not.toContain("<script>alert(1)</script>");
    expect(container.querySelector("script")).toBeNull();
    expect(container.textContent).toContain("<script>alert(1)</script>");
  });
});
