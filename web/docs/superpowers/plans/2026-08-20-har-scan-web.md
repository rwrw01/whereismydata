# har-scan-web Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A static, client-side web page (hosted on GitHub Pages) where a user drops a HAR file, gets it sanitized down to a bare hostname list entirely in the browser, and sees a flat table of which organisation (leverancier) operates each hostname and where that organisation is statutorily registered — sourced by calling the `har-provider-lookup` microservice.

**Architecture:** No framework, no backend of its own. A HAR parser module reads only `request.url` and the `Referer` header from each entry (immediately reduced to hostnames, nothing else ever touches a variable) and produces a minimal JSON payload. That payload is POSTed to `har-provider-lookup`'s `/lookup` endpoint; the response is merged with the local hostname counts and rendered as a table. Everything runs in the browser after the static bundle loads — no server-side rendering, no session state.

**Tech Stack:** TypeScript (`strict: true`), Vite (build + dev server), Vitest + jsdom (unit tests), Playwright (E2E), Biome (unified lint + format), npm with exact version pinning.

**Spec:** `C:\dev\har-scan-web\docs\superpowers\specs\2026-08-20-har-provider-scan-design.md`

**Depends on:** `har-provider-lookup` (sibling repo at `C:\dev\har-provider-lookup`, plan: `C:\dev\har-provider-lookup\docs\superpowers\plans\2026-08-20-har-provider-lookup.md`). Task 6 of this plan (E2E) starts that service via its `docker-compose.yml` and requires it to already be implemented.

## Global Constraints

- TypeScript `strict: true`, no `any`, ESM only (no CommonJS `require`).
- Sanitization is a strict whitelist: the parser reads only `entry.request.url` and the `Referer` request header value, both immediately reduced to a hostname via the `URL` constructor. No other HAR field (headers, cookies, bodies, query strings, timings) is ever assigned to a variable outside the read loop.
- Client-side upload size cap: 50 MB. Above that, reject with a Dutch error message before any parsing happens.
- `POST /lookup` requests are capped at 200 hostnames each (matches the backend's limit) — the lookup client batches larger hostname lists into multiple requests.
- No composite sovereignty score anywhere in this app. The table shows only: hostname, leverancier (`org_name`), statutaire zetel (`org_country`), a simple EU/niet-EU badge, and request count.
- Fully ephemeral: nothing is persisted (no localStorage, no backend of its own). State lives only in page memory for the current session.
- The lookup backend's URL is configured via the `VITE_LOOKUP_API_URL` build-time env var — never hardcoded in source.
- Biome is the single unified lint+format tool — no separate ESLint/Prettier setup.
- npm with `save-exact=true` (via `.npmrc`); `package-lock.json` is committed.
- `LICENSE` file (EUPL-1.2) at repo root — already present, copied from `soevereinscan`.
- `README.md` must contain a dependency license table, kept in sync when dependencies change.
- No `Co-Authored-By` lines for any AI model in any commit message.
- User-facing text (labels, error messages) in Dutch; code, comments, identifiers in English.
- Supply-chain hygiene on our own dependency choices (not on scanned data): every dependency is exact-pinned with a committed `package-lock.json` (already covered above), CI runs `npm audit --audit-level=high` on every push/PR, and Dependabot is configured to open update PRs for the `npm` and `github-actions` ecosystems weekly.

---

## File Structure

```
har-scan-web/
├── LICENSE                              # EUPL-1.2 (already present)
├── README.md
├── package.json
├── package-lock.json
├── .npmrc
├── .gitignore
├── .env.example
├── tsconfig.json
├── vite.config.ts                       # includes Vitest `test` config
├── biome.json
├── playwright.config.ts
├── index.html
├── src/
│   ├── main.ts                          # drag&drop wiring, orchestrates parse -> lookup -> render
│   ├── types.ts                         # shared types
│   ├── eu-countries.ts                  # EU_COUNTRIES set + isEuCountry()
│   ├── har-parser.ts                    # parseHar() — the sanitizer, most safety-critical file
│   ├── lookup-client.ts                 # lookupHostnames() — calls har-provider-lookup, batches, maps snake_case->camelCase
│   ├── render-table.ts                  # renderResultsTable() — XSS-safe DOM rendering
│   └── style.css
├── tests/
│   ├── fixtures/
│   │   └── dirty-sample.har             # HAR fixture containing cookies/auth headers/tokens, for sanitization tests
│   ├── eu-countries.test.ts
│   ├── har-parser.test.ts
│   ├── lookup-client.test.ts
│   └── render-table.test.ts
├── e2e/
│   ├── global-setup.ts                  # docker compose up for har-provider-lookup
│   ├── global-teardown.ts               # docker compose down
│   └── upload-and-lookup.spec.ts
└── .github/
    └── workflows/
        └── deploy-pages.yml
```

---

### Task 1: Tooling scaffolding + first testable unit (`eu-countries.ts`)

**Files:**
- Create: `package.json`
- Create: `.npmrc`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `tsconfig.json`
- Create: `vite.config.ts`
- Create: `biome.json`
- Create: `index.html`
- Create: `src/eu-countries.ts`
- Test: `tests/eu-countries.test.ts`

**Interfaces:**
- Produces: `EU_COUNTRIES: Set<string>`, `isEuCountry(countryCode: string | null): boolean` from `src/eu-countries.ts`.
- Consumed by: Task 4 (`render-table.ts`).

- [ ] **Step 1: Write `package.json`**

```json
{
  "name": "har-scan-web",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "license": "EUPL-1.2",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest",
    "check": "biome check .",
    "e2e": "cross-env VITE_LOOKUP_API_URL=http://localhost:8080 npm run build && playwright test"
  },
  "devDependencies": {
    "@biomejs/biome": "2.5.9",
    "@playwright/test": "1.62.1",
    "cross-env": "10.1.0",
    "jsdom": "30.0.1",
    "typescript": "7.0.2",
    "vite": "8.2.2",
    "vitest": "4.1.11"
  }
}
```

- [ ] **Step 2: Write `.npmrc`**

```
save-exact=true
```

- [ ] **Step 3: Write `.gitignore`**

```
node_modules/
dist/
.env
.env.local
playwright-report/
test-results/
```

- [ ] **Step 4: Write `.env.example`**

```
VITE_LOOKUP_API_URL=http://localhost:8080
```

- [ ] **Step 5: Write `tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitOverride": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "isolatedModules": true,
    "forceConsistentCasingInFileNames": true,
    "types": ["vite/client"]
  },
  "include": ["src", "tests", "vite.config.ts"]
}
```

- [ ] **Step 6: Write `vite.config.ts`** (also configures Vitest, per Vitest's recommended single-config setup)

```typescript
/// <reference types="vitest/config" />
import { defineConfig } from "vite";

export default defineConfig({
  test: {
    environment: "jsdom",
    include: ["tests/**/*.test.ts"],
  },
});
```

- [ ] **Step 7: Write `biome.json`**

```json
{
  "$schema": "https://biomejs.dev/schemas/2.5.9/schema.json",
  "linter": { "enabled": true, "rules": { "recommended": true } },
  "formatter": { "enabled": true, "indentStyle": "space", "indentWidth": 2 },
  "javascript": { "formatter": { "quoteStyle": "double" } }
}
```

- [ ] **Step 8: Write `index.html`**

```html
<!doctype html>
<html lang="nl">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>HAR Provider Scan</title>
  </head>
  <body>
    <main>
      <h1>HAR Provider Scan</h1>
      <p>
        Upload een HAR-bestand (geëxporteerd via de netwerktab van je
        browser devtools) om te zien welke leveranciers en landen erachter
        schuilgaan. Het bestand wordt lokaal in je browser verwerkt en
        verlaat nooit je computer in ruwe vorm — alleen hostnamen worden
        naar de lookup-service verstuurd.
      </p>
      <div id="drop-zone">
        <p>Sleep een .har-bestand hierheen, of kies een bestand:</p>
        <input id="file-input" type="file" accept=".har,application/json" />
      </div>
      <p id="status"></p>
      <div id="results"></div>
    </main>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
```

- [ ] **Step 9: Install dependencies**

Run: `npm install`
Expected: `package-lock.json` created/updated, `node_modules/` populated.

- [ ] **Step 10: Write the failing test — `tests/eu-countries.test.ts`**

```typescript
import { describe, expect, it } from "vitest";
import { EU_COUNTRIES, isEuCountry } from "../src/eu-countries";

describe("isEuCountry", () => {
  it("returns true for EU member states", () => {
    expect(isEuCountry("NL")).toBe(true);
    expect(isEuCountry("DE")).toBe(true);
  });

  it("returns false for non-EU countries", () => {
    expect(isEuCountry("US")).toBe(false);
    expect(isEuCountry("GB")).toBe(false);
  });

  it("returns false for null", () => {
    expect(isEuCountry(null)).toBe(false);
  });

  it("contains exactly the expected member states", () => {
    expect(EU_COUNTRIES.size).toBe(30);
  });
});
```

- [ ] **Step 11: Run test to verify it fails**

Run: `npm test`
Expected: FAIL — `Cannot find module '../src/eu-countries'`

- [ ] **Step 12: Write `src/eu-countries.ts`**

```typescript
export const EU_COUNTRIES = new Set([
  "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
  "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
  "PL", "PT", "RO", "SK", "SI", "ES", "SE",
  "IS", "LI", "NO",
]);

export function isEuCountry(countryCode: string | null): boolean {
  return countryCode !== null && EU_COUNTRIES.has(countryCode);
}
```

Note: this list is EU + EEA (IS, LI, NO) — 30 codes — deliberately *not* including
Switzerland or the wider adequacy-country list from `soevereinscan`'s
`classifier.py`. This tool shows a plain EU/EEA-membership fact, not the
adequacy-decision judgment call that `classifier.py` makes; keeping the
two lists visibly different avoids implying they mean the same thing.

- [ ] **Step 13: Run test to verify it passes**

Run: `npm test`
Expected: PASS

- [ ] **Step 14: Run Biome to verify formatting/lint compliance**

Run: `npm run check`
Expected: no errors (fix any formatting issues Biome reports, then re-run)

- [ ] **Step 15: Commit**

```bash
git add package.json package-lock.json .npmrc .gitignore .env.example tsconfig.json vite.config.ts biome.json index.html src/eu-countries.ts tests/eu-countries.test.ts
git commit -m "Scaffold Vite/TypeScript project with EU-country check"
```

---

### Task 2: HAR sanitizer (`har-parser.ts`) — the critical file

**Files:**
- Create: `src/types.ts`
- Create: `src/har-parser.ts`
- Create: `tests/fixtures/dirty-sample.har`
- Test: `tests/har-parser.test.ts`

**Interfaces:**
- Produces: `src/types.ts` — `HostnameCount { host: string; count: number }`, `HostnameEdge { parent: string; child: string }`, `ParsedHar { hostnames: HostnameCount[]; edges: HostnameEdge[] }`, `LookupResult { hostname: string; asn: number | null; orgName: string | null; orgCountry: string | null }`, `ResultRow { hostname: string; count: number; asn: number | null; orgName: string | null; orgCountry: string | null }`.
- Produces: `parseHar(rawText: string): ParsedHar`, `class InvalidHarError extends Error` from `src/har-parser.ts`.
- Consumed by: Task 5 (`main.ts`).

- [ ] **Step 1: Write `src/types.ts`**

```typescript
export interface HostnameCount {
  host: string;
  count: number;
}

export interface HostnameEdge {
  parent: string;
  child: string;
}

export interface ParsedHar {
  hostnames: HostnameCount[];
  edges: HostnameEdge[];
}

export interface LookupResult {
  hostname: string;
  asn: number | null;
  orgName: string | null;
  orgCountry: string | null;
}

export interface ResultRow {
  hostname: string;
  count: number;
  asn: number | null;
  orgName: string | null;
  orgCountry: string | null;
}
```

- [ ] **Step 2: Write the "dirty" test fixture — `tests/fixtures/dirty-sample.har`**

This fixture deliberately contains cookies, an `Authorization` bearer
token, a session token in a query string, and an email address in a
response body — everything the sanitizer must never surface.

```json
{
  "log": {
    "version": "1.2",
    "creator": { "name": "test-fixture", "version": "1.0" },
    "entries": [
      {
        "request": {
          "method": "GET",
          "url": "https://app.example.com/dashboard?session_token=SUPERSECRET123&user=alice",
          "headers": [
            { "name": "Cookie", "value": "sessionid=abcdef123456; auth=topsecret" },
            {
              "name": "Authorization",
              "value": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.secretpayload.sig"
            }
          ]
        },
        "response": {
          "status": 200,
          "headers": [{ "name": "Set-Cookie", "value": "sessionid=abcdef123456; HttpOnly" }],
          "content": { "text": "{\"email\":\"alice@example.com\",\"apiKey\":\"sk_live_secret\"}" }
        }
      },
      {
        "request": {
          "method": "GET",
          "url": "https://cdn.example.com/static/app.js",
          "headers": [
            {
              "name": "Referer",
              "value": "https://app.example.com/dashboard?session_token=SUPERSECRET123"
            }
          ]
        },
        "response": { "status": 200, "headers": [], "content": { "text": "" } }
      },
      {
        "request": {
          "method": "GET",
          "url": "https://cdn.example.com/static/logo.png",
          "headers": []
        },
        "response": { "status": 200, "headers": [], "content": { "text": "" } }
      }
    ]
  }
}
```

- [ ] **Step 3: Write the failing test — `tests/har-parser.test.ts`**

```typescript
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { InvalidHarError, parseHar } from "../src/har-parser";

const dirtyHarPath = fileURLToPath(new URL("./fixtures/dirty-sample.har", import.meta.url));
const dirtyHarText = readFileSync(dirtyHarPath, "utf-8");

describe("parseHar", () => {
  it("extracts hostnames with request counts", () => {
    const result = parseHar(dirtyHarText);
    expect(result.hostnames).toEqual(
      expect.arrayContaining([
        { host: "app.example.com", count: 1 },
        { host: "cdn.example.com", count: 2 },
      ])
    );
    expect(result.hostnames).toHaveLength(2);
  });

  it("builds a referer-based edge graph using only hostnames", () => {
    const result = parseHar(dirtyHarText);
    expect(result.edges).toEqual([{ parent: "app.example.com", child: "cdn.example.com" }]);
  });

  it("never leaks cookies, auth headers, tokens, emails or query strings into the parsed result", () => {
    const result = parseHar(dirtyHarText);
    const serialized = JSON.stringify(result);

    const secrets = [
      "SUPERSECRET123",
      "sessionid",
      "topsecret",
      "sk_live_secret",
      "alice@example.com",
      "Bearer",
      "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
      "session_token",
    ];
    for (const secret of secrets) {
      expect(serialized).not.toContain(secret);
    }
  });

  it("throws InvalidHarError on invalid JSON", () => {
    expect(() => parseHar("not json")).toThrow(InvalidHarError);
  });

  it("throws InvalidHarError when there are no entries", () => {
    expect(() => parseHar(JSON.stringify({ log: { entries: [] } }))).toThrow(InvalidHarError);
  });

  it("throws InvalidHarError when log.entries is missing entirely", () => {
    expect(() => parseHar(JSON.stringify({ log: {} }))).toThrow(InvalidHarError);
  });

  it("skips entries with an unparseable request URL instead of throwing", () => {
    const har = JSON.stringify({
      log: { entries: [{ request: { url: "not a url", headers: [] } }] },
    });
    const result = parseHar(har);
    expect(result.hostnames).toEqual([]);
  });
});
```

- [ ] **Step 4: Run test to verify it fails**

Run: `npm test`
Expected: FAIL — `Cannot find module '../src/har-parser'`

- [ ] **Step 5: Write `src/har-parser.ts`**

```typescript
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
      "Kon HAR-bestand niet lezen — is dit een geldig HAR-exportbestand?"
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

  const hostnames = Array.from(counts.entries()).map(([host, count]) => ({ host, count }));

  return { hostnames, edges };
}
```

- [ ] **Step 6: Run test to verify it passes**

Run: `npm test`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/types.ts src/har-parser.ts tests/fixtures/dirty-sample.har tests/har-parser.test.ts
git commit -m "Add HAR sanitizer with whitelist extraction of hostnames only"
```

---

### Task 3: Lookup client (`lookup-client.ts`)

**Files:**
- Create: `src/lookup-client.ts`
- Test: `tests/lookup-client.test.ts`

**Interfaces:**
- Consumes: `LookupResult` type (Task 2).
- Produces: `lookupHostnames(apiBaseUrl: string, hostnames: string[]): Promise<LookupResult[]>`, `class LookupApiError extends Error` from `src/lookup-client.ts`.
- Consumed by: Task 5 (`main.ts`).

- [ ] **Step 1: Write the failing test — `tests/lookup-client.test.ts`**

```typescript
import { afterEach, describe, expect, it, vi } from "vitest";
import { LookupApiError, lookupHostnames } from "../src/lookup-client";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("lookupHostnames", () => {
  it("maps snake_case API response fields to camelCase results", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        results: [
          { hostname: "example.com", asn: 15169, org_name: "Google LLC", org_country: "US" },
        ],
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const results = await lookupHostnames("https://api.example.invalid", ["example.com"]);

    expect(results).toEqual([
      { hostname: "example.com", asn: 15169, orgName: "Google LLC", orgCountry: "US" },
    ]);
    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.invalid/lookup",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ hostnames: ["example.com"] }),
      })
    );
  });

  it("splits requests into batches of at most 200 hostnames", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ results: [] }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const hostnames = Array.from({ length: 250 }, (_, i) => `h${i}.example.com`);
    await lookupHostnames("https://api.example.invalid", hostnames);

    expect(fetchMock).toHaveBeenCalledTimes(2);
    const firstBody = JSON.parse((fetchMock.mock.calls[0][1] as RequestInit).body as string);
    const secondBody = JSON.parse((fetchMock.mock.calls[1][1] as RequestInit).body as string);
    expect(firstBody.hostnames).toHaveLength(200);
    expect(secondBody.hostnames).toHaveLength(50);
  });

  it("throws LookupApiError on a non-ok response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 503, json: async () => ({}) })
    );

    await expect(lookupHostnames("https://api.example.invalid", ["a.com"])).rejects.toThrow(
      LookupApiError
    );
  });

  it("throws LookupApiError when the network request itself fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    await expect(lookupHostnames("https://api.example.invalid", ["a.com"])).rejects.toThrow(
      LookupApiError
    );
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test`
Expected: FAIL — `Cannot find module '../src/lookup-client'`

- [ ] **Step 3: Write `src/lookup-client.ts`**

```typescript
import type { LookupResult } from "./types";

const MAX_HOSTNAMES_PER_REQUEST = 200;

export class LookupApiError extends Error {}

interface ApiLookupResult {
  hostname: string;
  asn: number | null;
  org_name: string | null;
  org_country: string | null;
}

interface ApiLookupResponse {
  results: ApiLookupResult[];
}

function chunk<T>(items: T[], size: number): T[][] {
  const chunks: T[][] = [];
  for (let i = 0; i < items.length; i += size) {
    chunks.push(items.slice(i, i + size));
  }
  return chunks;
}

async function lookupBatch(apiBaseUrl: string, hostnames: string[]): Promise<LookupResult[]> {
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl}/lookup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ hostnames }),
    });
  } catch {
    throw new LookupApiError("Kon geen verbinding maken met de lookup-service.");
  }

  if (!response.ok) {
    throw new LookupApiError(`Lookup-service gaf een fout terug (status ${response.status}).`);
  }

  const data = (await response.json()) as ApiLookupResponse;
  return data.results.map((r) => ({
    hostname: r.hostname,
    asn: r.asn,
    orgName: r.org_name,
    orgCountry: r.org_country,
  }));
}

export async function lookupHostnames(
  apiBaseUrl: string,
  hostnames: string[]
): Promise<LookupResult[]> {
  const batches = chunk(hostnames, MAX_HOSTNAMES_PER_REQUEST);
  const batchResults = await Promise.all(batches.map((batch) => lookupBatch(apiBaseUrl, batch)));
  return batchResults.flat();
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/lookup-client.ts tests/lookup-client.test.ts
git commit -m "Add lookup client with request batching and snake_case mapping"
```

---

### Task 4: Result table rendering (`render-table.ts`)

**Files:**
- Create: `src/render-table.ts`
- Test: `tests/render-table.test.ts`

**Interfaces:**
- Consumes: `ResultRow` type (Task 2), `isEuCountry` (Task 1).
- Produces: `renderResultsTable(container: HTMLElement, rows: ResultRow[]): void` from `src/render-table.ts`.
- Consumed by: Task 5 (`main.ts`).

- [ ] **Step 1: Write the failing test — `tests/render-table.test.ts`**

```typescript
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test`
Expected: FAIL — `Cannot find module '../src/render-table'`

- [ ] **Step 3: Write `src/render-table.ts`**

```typescript
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/render-table.ts tests/render-table.test.ts
git commit -m "Add XSS-safe result table rendering"
```

---

### Task 5: Wire it together — `main.ts`, `style.css`

**Files:**
- Create: `src/main.ts`
- Create: `src/style.css`
- Modify: `index.html` (add stylesheet link)

**Interfaces:**
- Consumes: `parseHar`, `InvalidHarError` (Task 2); `lookupHostnames`, `LookupApiError` (Task 3); `renderResultsTable` (Task 4); `ResultRow` (Task 2).

This task has no dedicated unit test file — it is thin DOM-event wiring
that composes already-tested units. It is exercised end-to-end by
Task 6's Playwright test, per the plan's testing strategy (unit tests for
logic, one E2E test for the full user flow).

- [ ] **Step 1: Write `src/style.css`**

```css
body {
  font-family: system-ui, sans-serif;
  max-width: 900px;
  margin: 2rem auto;
  padding: 0 1rem;
  color: #1a1a1a;
}

#drop-zone {
  border: 2px dashed #888;
  border-radius: 8px;
  padding: 2rem;
  text-align: center;
  margin: 1rem 0;
}

#drop-zone.drag-over {
  border-color: #2563eb;
  background: #eff6ff;
}

.results-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 1rem;
}

.results-table th,
.results-table td {
  text-align: left;
  padding: 0.5rem;
  border-bottom: 1px solid #ddd;
}
```

- [ ] **Step 2: Modify `index.html`** — add the stylesheet link inside `<head>`

```html
<link rel="stylesheet" href="/src/style.css" />
```

(insert this line directly after the `<meta name="viewport" ...>` line added in Task 1)

- [ ] **Step 3: Write `src/main.ts`**

```typescript
import { InvalidHarError, parseHar } from "./har-parser";
import { LookupApiError, lookupHostnames } from "./lookup-client";
import { renderResultsTable } from "./render-table";
import "./style.css";
import type { ResultRow } from "./types";

const MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024;
const LOOKUP_API_URL = import.meta.env.VITE_LOOKUP_API_URL as string;

const dropZone = document.querySelector<HTMLElement>("#drop-zone");
const fileInput = document.querySelector<HTMLInputElement>("#file-input");
const statusEl = document.querySelector<HTMLElement>("#status");
const resultsEl = document.querySelector<HTMLElement>("#results");

if (!dropZone || !fileInput || !statusEl || !resultsEl) {
  throw new Error("Verwachte pagina-elementen ontbreken.");
}

function setStatus(message: string): void {
  statusEl.textContent = message;
}

async function handleFile(file: File): Promise<void> {
  resultsEl.innerHTML = "";

  if (file.size > MAX_FILE_SIZE_BYTES) {
    setStatus("Bestand is te groot (max 50 MB).");
    return;
  }

  let text: string;
  try {
    text = await file.text();
  } catch {
    setStatus("Kon het bestand niet lezen.");
    return;
  }

  try {
    const parsed = parseHar(text);
    setStatus(`${parsed.hostnames.length} hostnamen gevonden, leveranciers opzoeken...`);

    const lookups = await lookupHostnames(
      LOOKUP_API_URL,
      parsed.hostnames.map((h) => h.host)
    );
    const lookupByHost = new Map(lookups.map((l) => [l.hostname, l]));

    const rows: ResultRow[] = parsed.hostnames.map((h) => {
      const lookup = lookupByHost.get(h.host);
      return {
        hostname: h.host,
        count: h.count,
        asn: lookup?.asn ?? null,
        orgName: lookup?.orgName ?? null,
        orgCountry: lookup?.orgCountry ?? null,
      };
    });

    setStatus(`${rows.length} hostnamen geanalyseerd.`);
    renderResultsTable(resultsEl, rows);
  } catch (error) {
    if (error instanceof InvalidHarError || error instanceof LookupApiError) {
      setStatus(error.message);
      return;
    }
    setStatus("Er ging iets onverwachts mis.");
  }
}

fileInput.addEventListener("change", () => {
  const file = fileInput.files?.[0];
  if (file) void handleFile(file);
});

dropZone.addEventListener("dragover", (event) => {
  event.preventDefault();
  dropZone.classList.add("drag-over");
});

dropZone.addEventListener("dragleave", () => {
  dropZone.classList.remove("drag-over");
});

dropZone.addEventListener("drop", (event) => {
  event.preventDefault();
  dropZone.classList.remove("drag-over");
  const file = event.dataTransfer?.files?.[0];
  if (file) void handleFile(file);
});
```

- [ ] **Step 4: Verify the app runs and the toolchain is clean**

Run: `npm run check`
Expected: no Biome errors
Run: `npx tsc -b --noEmit`
Expected: no type errors
Run: `npm run dev` — open the printed local URL, confirm the upload page renders with the drop zone and file input visible. Stop the dev server (Ctrl+C) once confirmed.

- [ ] **Step 5: Commit**

```bash
git add src/main.ts src/style.css index.html
git commit -m "Wire up drag-and-drop upload, lookup call and result rendering"
```

---

### Task 6: End-to-end test against a real `har-provider-lookup` instance

**Files:**
- Create: `playwright.config.ts`
- Create: `e2e/global-setup.ts`
- Create: `e2e/global-teardown.ts`
- Create: `e2e/upload-and-lookup.spec.ts`

**Interfaces:**
- Consumes: `har-provider-lookup`'s `docker-compose.yml` at `../har-provider-lookup/docker-compose.yml` (sibling repo checkout — see "Depends on" in the plan header) and its `POST /lookup` contract (Task 7 of that repo's plan).

**Precondition:** `har-provider-lookup` must be fully implemented (its own plan, Tasks 1-8) and checked out as a sibling directory at `C:\dev\har-provider-lookup`, before this task can run for real. If it isn't yet, implement that plan first — do not write this task's tests against a mocked backend; the whole point of this E2E test is exercising the real service.

- [ ] **Step 1: Write `playwright.config.ts`**

```typescript
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  globalSetup: "./e2e/global-setup.ts",
  globalTeardown: "./e2e/global-teardown.ts",
  webServer: {
    command: "npm run preview -- --port 4173",
    url: "http://localhost:4173",
    reuseExistingServer: !process.env.CI,
  },
  use: {
    baseURL: "http://localhost:4173",
  },
});
```

- [ ] **Step 2: Write `e2e/global-setup.ts`**

```typescript
import { execSync } from "node:child_process";

export default function globalSetup(): void {
  execSync("docker compose -f ../har-provider-lookup/docker-compose.yml up -d --build --wait", {
    stdio: "inherit",
  });
}
```

- [ ] **Step 3: Write `e2e/global-teardown.ts`**

```typescript
import { execSync } from "node:child_process";

export default function globalTeardown(): void {
  execSync("docker compose -f ../har-provider-lookup/docker-compose.yml down", {
    stdio: "inherit",
  });
}
```

- [ ] **Step 4: Write `e2e/upload-and-lookup.spec.ts`**

```typescript
import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";

const dirtyHarPath = fileURLToPath(
  new URL("../tests/fixtures/dirty-sample.har", import.meta.url)
);

test("uploading a HAR file shows a results table with leverancier and zetel", async ({
  page,
}) => {
  await page.goto("/");

  const fileInput = page.locator("#file-input");
  await fileInput.setInputFiles(path.resolve(dirtyHarPath));

  await expect(page.locator("#status")).toContainText("hostnamen geanalyseerd", {
    timeout: 15_000,
  });

  const table = page.locator(".results-table");
  await expect(table).toBeVisible();
  await expect(table).toContainText("app.example.com");
  await expect(table).toContainText("cdn.example.com");

  // The dirty fixture's secrets must never reach the rendered page either.
  const pageContent = await page.content();
  expect(pageContent).not.toContain("SUPERSECRET123");
  expect(pageContent).not.toContain("sk_live_secret");
});

test("rejects a file that is not valid JSON", async ({ page }) => {
  await page.goto("/");

  await page.evaluate(() => {
    const input = document.querySelector<HTMLInputElement>("#file-input");
    const dataTransfer = new DataTransfer();
    dataTransfer.items.add(new File(["not json"], "broken.har", { type: "application/json" }));
    if (input) input.files = dataTransfer.files;
    input?.dispatchEvent(new Event("change", { bubbles: true }));
  });

  await expect(page.locator("#status")).toContainText("Kon HAR-bestand niet lezen");
});
```

- [ ] **Step 5: Install Playwright browsers**

Run: `npx playwright install --with-deps chromium`

- [ ] **Step 6: Run the E2E suite for real and confirm it passes**

Run: `npm run e2e`
Expected: both tests PASS. This actually starts `har-provider-lookup` via Docker Compose, builds and previews `har-scan-web`, and drives a real browser — per the project's E2E rule, this must be run and confirmed green here, not asserted without running it.
Run: `docker compose -f ../har-provider-lookup/docker-compose.yml down` if the teardown didn't already stop it (confirm with `docker compose -f ../har-provider-lookup/docker-compose.yml ps`).

- [ ] **Step 7: Commit**

```bash
git add playwright.config.ts e2e
git commit -m "Add end-to-end test against a real har-provider-lookup instance"
```

---

### Task 7: GitHub Pages deployment workflow + final README

**Files:**
- Create: `.github/workflows/deploy-pages.yml`
- Modify: `README.md`

- [ ] **Step 1: Write `.github/workflows/deploy-pages.yml`**

```yaml
name: Deploy to GitHub Pages

on:
  push:
    branches: [main]

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm
      - run: npm ci
      - run: npm run check
      - run: npm test
      - run: npm run build
        env:
          VITE_LOOKUP_API_URL: ${{ vars.LOOKUP_API_URL }}
      - uses: actions/upload-pages-artifact@v3
        with:
          path: dist

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

Note for implementer: this workflow reads `VITE_LOOKUP_API_URL` from a
repository variable named `LOOKUP_API_URL` (Settings → Secrets and
variables → Actions → Variables), not from a secret — the URL of a
public lookup API is not sensitive. Set it once `har-provider-lookup` is
deployed and its public URL is known; this is one of the spec's "Open
punten voor implementatiefase" (hosting choice) and isn't resolved by
this plan.

- [ ] **Step 2: Enable GitHub Pages for the repository**

In the GitHub repository settings, under "Pages", set the source to
"GitHub Actions" (not "Deploy from a branch"). This is a one-time manual
step in the GitHub UI, not something this plan can script.

- [ ] **Step 3: Write the final `README.md`**

```markdown
# har-scan-web

Statische, client-side webpagina waar je een HAR-bestand kunt uploaden om
te zien welke leveranciers en landen erachter schuilgaan — zonder dat het
bestand ooit in ruwe vorm je browser verlaat.

Sanitizing gebeurt volledig lokaal: alleen hostnamen (en hoe vaak ze
worden aangeroepen) worden naar de lookup-backend
([har-provider-lookup](../har-provider-lookup)) gestuurd. Cookies,
auth-headers, request/response-bodies en query strings worden nooit
gelezen buiten het moment van hostname-extractie.

## Ontwikkelen

\`\`\`bash
npm install
cp .env.example .env
npm run dev
\`\`\`

Vereist een lokaal draaiende `har-provider-lookup` op de URL uit
`VITE_LOOKUP_API_URL` (standaard `http://localhost:8080`) — zie de
README van die repo.

## Testen

\`\`\`bash
npm test              # unit tests (Vitest)
npm run check          # lint + format (Biome)
npm run e2e             # end-to-end (Playwright, start har-provider-lookup via Docker eerst — zie playwright.config.ts)
\`\`\`

## Bouwen

\`\`\`bash
npm run build
\`\`\`

Output in `dist/`, gepubliceerd naar GitHub Pages via
`.github/workflows/deploy-pages.yml` bij elke push naar `main`.

## License

EUPL-1.2 — zie [LICENSE](LICENSE).

## Dependencies

| Package | License |
|---|---|
| typescript (dev) | Apache-2.0 |
| vite (dev) | MIT |
| vitest (dev) | MIT |
| jsdom (dev) | MIT |
| @playwright/test (dev) | Apache-2.0 |
| @biomejs/biome (dev) | MIT |
| cross-env (dev) | MIT |
```

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/deploy-pages.yml README.md
git commit -m "Add GitHub Pages deployment workflow and final README"
```

---

### Task 8: Supply-chain scanning — CI dependency audit + Dependabot

Added after user feedback: the concern is not scanning data users
submit, it's making sure *we* don't introduce vulnerable software by
pulling in compromised or outdated npm packages ourselves. `npm audit`
checks the resolved lockfile against the npm advisory database;
Dependabot keeps dependencies from silently going stale.

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `.github/dependabot.yml`
- Modify: `.github/workflows/deploy-pages.yml`

- [ ] **Step 1: Write `.github/workflows/ci.yml`** (runs on every push and PR — `deploy-pages.yml` only runs on push to `main`, so PRs need their own gate)

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm
      - run: npm ci
      - run: npm run check
      - run: npm test
      - run: npm audit --audit-level=high
```

- [ ] **Step 2: Write `.github/dependabot.yml`**

```yaml
version: 2
updates:
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "weekly"
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
```

- [ ] **Step 3: Modify `.github/workflows/deploy-pages.yml`** — add the same audit step so a deploy can't ship a build with a known-high-severity vulnerability, even if CI was somehow skipped

Insert this step in the `build` job, directly after the existing `npm run check` step and before `npm test`:

```yaml
      - run: npm audit --audit-level=high
```

- [ ] **Step 4: Run the audit locally to confirm the current lockfile is clean**

Run: `npm audit --audit-level=high`
Expected: exits 0, no high/critical advisories in the dependency set as
scaffolded by Tasks 1-7. If it reports a finding, resolve it (`npm audit
fix`, or a manual version bump if `fix` can't resolve it) before
committing — do not silence or skip a real finding here.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/ci.yml .github/dependabot.yml .github/workflows/deploy-pages.yml
git commit -m "Add CI dependency audit and Dependabot config"
```

---

## Self-Review Notes

- **Spec coverage**: whitelist sanitization (Task 2, verified by the dirty-fixture test), 50 MB client-side size cap (Task 5), 200-hostname batching matching the backend cap (Task 3), no composite score / only leverancier+zetel+EU-badge+count (Task 4), fully ephemeral (no storage code anywhere in this plan — confirmed absent), `VITE_LOOKUP_API_URL` env-var-driven backend URL (Tasks 1, 5, 7), Biome as single lint/format tool (Task 1), npm exact pinning via `.npmrc` (Task 1), EUPL-1.2 LICENSE (already present) + README dependency table (Task 7), GitHub Pages deployment (Task 7), real E2E run against the real backend (Task 6), supply-chain dependency scanning (Task 8, added on user feedback after the initial spec/plan were written). Not covered by this plan: the actual GitHub repository creation/push and the `LOOKUP_API_URL` Actions variable value, both of which depend on `har-provider-lookup` being deployed first (listed as open points in the spec).
- **Type consistency**: `LookupResult` (Task 2's `types.ts`) fields (`hostname`, `asn`, `orgName`, `orgCountry`) match what `lookup-client.ts` (Task 3) constructs and what `main.ts` (Task 5) reads via `lookup?.asn` / `lookup?.orgName` / `lookup?.orgCountry`. `ResultRow` matches what `render-table.ts` (Task 4) destructures (`r.hostname`, `r.orgName`, `r.orgCountry`, `r.count`) and what `main.ts` constructs. `ParsedHar.hostnames[].host` (Task 2) matches `main.ts`'s `h.host` usage (Task 5).
- **No placeholders**: the one deliberately-deferred value is the `LOOKUP_API_URL` Actions variable (Task 7, Step 1 note) — explicitly called out as depending on a not-yet-made hosting decision from the spec's open points, not silently glossed over.
