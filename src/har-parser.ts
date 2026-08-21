import type { HostnameEdge, ParsedHar } from "./types";

export class InvalidHarError extends Error {}

interface HarHeader {
  name: string;
  value: string;
}

interface HarEntry {
  request?: {
    url?: string;
    headers?: HarHeader[];
  };
}

interface HarFile {
  log?: {
    entries?: HarEntry[];
  };
}

function extractHostname(url: string): string | null {
  try {
    return new URL(url).hostname || null;
  } catch {
    return null;
  }
}

function extractRefererHostname(entry: HarEntry): string | null {
  const headers = entry.request?.headers ?? [];
  const referer = headers.find((h) => h.name.toLowerCase() === "referer");
  if (!referer) return null;
  return extractHostname(referer.value);
}

export function parseHar(rawText: string): ParsedHar {
  let data: HarFile;
  try {
    data = JSON.parse(rawText) as HarFile;
  } catch {
    throw new InvalidHarError(
      "Kon HAR-bestand niet lezen — is dit een geldig HAR-exportbestand?",
    );
  }

  const entries = data.log?.entries;
  if (!entries || entries.length === 0) {
    throw new InvalidHarError("Geen requests gevonden in dit bestand.");
  }

  const counts = new Map<string, number>();
  const edgeKeys = new Set<string>();
  const edges: HostnameEdge[] = [];

  for (const entry of entries) {
    const host = extractHostname(entry.request?.url ?? "");
    if (!host) continue;

    counts.set(host, (counts.get(host) ?? 0) + 1);

    const refererHost = extractRefererHostname(entry);
    if (refererHost && refererHost !== host) {
      const key = `${refererHost}->${host}`;
      if (!edgeKeys.has(key)) {
        edgeKeys.add(key);
        edges.push({ parent: refererHost, child: host });
      }
    }
  }

  const hostnames = Array.from(counts.entries()).map(([host, count]) => ({
    host,
    count,
  }));

  return { hostnames, edges };
}
