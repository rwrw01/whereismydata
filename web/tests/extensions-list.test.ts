import { describe, expect, it } from "vitest";
import { renderExtensionsList } from "../src/extensions-list";

describe("renderExtensionsList", () => {
  it("lists detected extension IDs", () => {
    const container = document.createElement("div");
    renderExtensionsList(container, ["abc123", "def456"]);

    const items = container.querySelectorAll("li");
    expect(items).toHaveLength(2);
    expect(container.textContent).toContain("abc123");
    expect(container.textContent).toContain("def456");
  });

  it("renders nothing when there are no extensions", () => {
    const container = document.createElement("div");
    renderExtensionsList(container, []);
    expect(container.innerHTML).toBe("");
  });

  it("escapes extension IDs to prevent XSS", () => {
    const container = document.createElement("div");
    renderExtensionsList(container, ["<script>alert(1)</script>"]);

    expect(container.querySelector("script")).toBeNull();
    expect(container.textContent).toContain("<script>alert(1)</script>");
  });
});
