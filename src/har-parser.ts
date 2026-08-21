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

// Mirrors the hostname validation the lookup backend enforces. Keeping the
// stricter side of the contract on the client stops a single unsupported
// hostname (e.g. a bracketed IPv6 literal such as "[::1]", which is a valid
// URL hostname but is rejected by the backend with a 422) from failing the
// whole batched lookup request. IPv4 literals like "192.168.1.5" still match.
const HOSTNAME_PATTERN = /^[A-Za-z0-9._-]+$/;

function extractHostname(url: string): string | null {
  try {
    const parsed = new URL(url);
    if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
      return null;
    }
    if (!HOSTNAME_PATTERN.test(parsed.hostname)) {
      return null;
    }
    return parsed.hostname || null;
  } catch {
    return null;
  }
}

function extractRefererHostname(entry: HarEntry): string | null {
  const headers = entry.request?.headers;
  if (!Array.isArray(headers)) return null;
  const referer = headers.find(
    (h) => typeof h?.name === "string" && h.name.toLowerCase() === "referer",
  );
  if (!referer || typeof referer.value !== "string") return null;
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
  if (!Array.isArray(entries) || entries.length === 0) {
    throw new InvalidHarError("Geen requests gevonden in dit bestand.");
  }

  const counts = new Map<string, number>();
  const edgeKeys = new Set<string>();
  const edges: HostnameEdge[] = [];

  for (const entry of entries) {
    try {
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
    } catch {
      // A single malformed entry must not abort parsing the whole file.
    }
  }

  const hostnames = Array.from(counts.entries()).map(([host, count]) => ({
    host,
    count,
  }));

  return { hostnames, edges };
}
