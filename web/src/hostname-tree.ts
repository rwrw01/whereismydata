import { escapeHtml } from "./render-table";
import type { HostnameEdge } from "./types";

interface TreeNode {
  host: string;
  children: TreeNode[];
}

function buildForest(edges: HostnameEdge[], allHosts: string[]): TreeNode[] {
  const childrenOf = new Map<string, string[]>();
  const hasParent = new Set<string>();

  for (const edge of edges) {
    const existing = childrenOf.get(edge.parent) ?? [];
    existing.push(edge.child);
    childrenOf.set(edge.parent, existing);
    hasParent.add(edge.child);
  }

  function build(host: string, visited: Set<string>): TreeNode {
    if (visited.has(host)) return { host, children: [] };
    const nextVisited = new Set(visited).add(host);
    const children = (childrenOf.get(host) ?? []).sort();
    return { host, children: children.map((c) => build(c, nextVisited)) };
  }

  const roots = allHosts.filter((h) => !hasParent.has(h));
  return roots.map((h) => build(h, new Set()));
}

function renderNode(node: TreeNode): string {
  const childrenHtml =
    node.children.length > 0
      ? `<ul>${node.children.map(renderNode).join("")}</ul>`
      : "";
  return `<li>${escapeHtml(node.host)}${childrenHtml}</li>`;
}

/** Renders the referer-based call order (which hostname's response led to
 * the next request) — e.g. to show an auth redirect happened before the
 * target webapp loaded. Built entirely from already-sanitized hostnames
 * (ParsedHar.edges); reads nothing new from the HAR. */
export function renderHostnameTree(
  container: HTMLElement,
  edges: HostnameEdge[],
  allHosts: string[],
): void {
  if (edges.length === 0) {
    container.innerHTML = "";
    return;
  }
  const roots = buildForest(edges, allHosts);
  container.innerHTML = `
    <h2>Volgorde van aanroepen</h2>
    <ul class="hostname-tree">${roots.map(renderNode).join("")}</ul>`;
}
