import { describe, expect, it } from "vitest";
import { renderHostnameTree } from "../src/hostname-tree";
import type { HostnameEdge } from "../src/types";

describe("renderHostnameTree", () => {
  it("renders a nested list following the referer chain", () => {
    const container = document.createElement("div");
    const edges: HostnameEdge[] = [
      { parent: "login.microsoftonline.com", child: "app.example.com" },
      { parent: "app.example.com", child: "cdn.example.com" },
    ];
    const allHosts = [
      "login.microsoftonline.com",
      "app.example.com",
      "cdn.example.com",
    ];

    renderHostnameTree(container, edges, allHosts);

    const root = container.querySelector("ul.hostname-tree > li");
    expect(root?.textContent).toContain("login.microsoftonline.com");
    const nested = container.querySelectorAll("li");
    expect(nested).toHaveLength(3);
  });

  it("renders nothing when there are no edges", () => {
    const container = document.createElement("div");
    renderHostnameTree(container, [], ["example.com"]);
    expect(container.innerHTML).toBe("");
  });

  it("escapes hostnames to prevent XSS", () => {
    const container = document.createElement("div");
    const edges: HostnameEdge[] = [
      { parent: "<script>alert(1)</script>", child: "child.example.com" },
    ];
    renderHostnameTree(container, edges, [
      "<script>alert(1)</script>",
      "child.example.com",
    ]);

    expect(container.querySelector("script")).toBeNull();
    expect(container.textContent).toContain("<script>alert(1)</script>");
  });
});
