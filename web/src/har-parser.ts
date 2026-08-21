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
  response?: {
    headers?: HarHeader[];
  };
}

interface HarFile {
  log?: {
    entries?: HarEntry[];
  };
}

// The whitelist this file enforces: request.url and the Referer request
// header VALUE (both reduced immediately to a hostname), plus — as of the
// cookie-count feature — response header NAMES only. A header's presence
// (e.g. "was there a Set-Cookie header at all") is not the same class of
// data as its value; counting occurrences of the name "set-cookie" never
// reads what was actually set. No other field (request/response bodies,
// query strings, timings, any other header's value) is ever read.

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

const EXTENSION_PROTOCOLS = new Set(["chrome-extension:", "moz-extension:"]);

// Browser-extension requests are never sent to the lookup backend (an
// extension ID has no ASN/PeeringDB entry, and treating it as a hostname
// would leak the visitor's specific installed extension). They are
// collected separately, for local-only display.
function extractExtensionId(url: string): string | null {
  try {
    const parsed = new URL(url);
    if (!EXTENSION_PROTOCOLS.has(parsed.protocol)) return null;
    return parsed.hostname || null;
  } catch {
    return null;
  }
}

// Counts Set-Cookie response headers by NAME only — never reads a header's
// value. A response can carry multiple Set-Cookie headers (one per cookie);
// this returns how many, so callers can show "N cookies set" without ever
// knowing which cookies or what they contained.
function countSetCookieHeaders(entry: HarEntry): number {
  const headers = entry.response?.headers;
  if (!Array.isArray(headers)) return 0;
  return headers.filter(
    (h) => typeof h?.name === "string" && h.name.toLowerCase() === "set-cookie",
  ).length;
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
  const cookieCounts = new Map<string, number>();
  const edgeKeys = new Set<string>();
  const edges: HostnameEdge[] = [];
  const extensions = new Set<string>();

  for (const entry of entries) {
    try {
      const url = entry.request?.url ?? "";
      const extensionId = extractExtensionId(url);
      if (extensionId) {
        extensions.add(extensionId);
        continue;
      }

      const host = extractHostname(url);
      if (!host) continue;

      counts.set(host, (counts.get(host) ?? 0) + 1);
      cookieCounts.set(
        host,
        (cookieCounts.get(host) ?? 0) + countSetCookieHeaders(entry),
      );

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
    cookieCount: cookieCounts.get(host) ?? 0,
  }));

  return { hostnames, edges, extensions: Array.from(extensions) };
}
