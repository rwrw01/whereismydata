// @vitest-environment node
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { InvalidHarError, parseHar } from "../src/har-parser";

const dirtyHarPath = fileURLToPath(
  new URL("./fixtures/dirty-sample.har", import.meta.url),
);
const dirtyHarText = readFileSync(dirtyHarPath, "utf-8");

describe("parseHar", () => {
  it("extracts hostnames with request counts", () => {
    const result = parseHar(dirtyHarText);
    expect(result.hostnames).toEqual(
      expect.arrayContaining([
        { host: "app.example.com", count: 1 },
        { host: "cdn.example.com", count: 2 },
      ]),
    );
    expect(result.hostnames).toHaveLength(2);
  });

  it("builds a referer-based edge graph using only hostnames", () => {
    const result = parseHar(dirtyHarText);
    expect(result.edges).toEqual([
      { parent: "app.example.com", child: "cdn.example.com" },
    ]);
  });

  it("never leaks cookies, auth headers, tokens, emails or query strings into the parsed result", () => {
    const result = parseHar(dirtyHarText);

    // Structural backstop: the return value must have exactly these two
    // keys, no matter what fields a future change might start reading off
    // a HAR entry. This catches a whole class of leak that a substring
    // search below would miss (e.g. a new field added under an existing
    // key name).
    expect(Object.keys(result).sort()).toEqual(["edges", "hostnames"]);

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
      "secretpayload",
      "abcdef123456",
      "/dashboard",
      "Authorization",
      "COOKIE_ARRAY_SECRET",
      "QUERYSTRING_SECRET",
      "POSTDATA_SECRET",
      "RESPONSE_COOKIE_SECRET",
      "1.2.3.4",
    ];
    for (const secret of secrets) {
      expect(serialized).not.toContain(secret);
    }
  });

  it("throws InvalidHarError on invalid JSON", () => {
    expect(() => parseHar("not json")).toThrow(InvalidHarError);
  });

  it("throws InvalidHarError when there are no entries", () => {
    expect(() => parseHar(JSON.stringify({ log: { entries: [] } }))).toThrow(
      InvalidHarError,
    );
  });

  it("throws InvalidHarError when log.entries is missing entirely", () => {
    expect(() => parseHar(JSON.stringify({ log: {} }))).toThrow(
      InvalidHarError,
    );
  });

  it("skips entries with an unparseable request URL instead of throwing", () => {
    const har = JSON.stringify({
      log: { entries: [{ request: { url: "not a url", headers: [] } }] },
    });
    const result = parseHar(har);
    expect(result.hostnames).toEqual([]);
  });

  it("throws InvalidHarError when log.entries is an object instead of an array", () => {
    const har = JSON.stringify({ log: { entries: { notAnArray: true } } });
    expect(() => parseHar(har)).toThrow(InvalidHarError);
  });

  it("skips a header with a null name instead of throwing", () => {
    const har = JSON.stringify({
      log: {
        entries: [
          {
            request: {
              url: "https://example.com/",
              headers: [{ name: null, value: "https://referer.example.com/" }],
            },
          },
        ],
      },
    });
    const result = parseHar(har);
    expect(result.hostnames).toEqual([{ host: "example.com", count: 1 }]);
    expect(result.edges).toEqual([]);
  });

  it("treats a non-array request.headers as no headers instead of throwing", () => {
    const har = JSON.stringify({
      log: {
        entries: [
          {
            request: { url: "https://example.com/", headers: "not-an-array" },
          },
        ],
      },
    });
    const result = parseHar(har);
    expect(result.hostnames).toEqual([{ host: "example.com", count: 1 }]);
    expect(result.edges).toEqual([]);
  });

  it("does not surface a chrome-extension:// URL as a hostname", () => {
    const har = JSON.stringify({
      log: {
        entries: [
          {
            request: {
              url: "chrome-extension://kjfhgabcdefghijklmnopqrstuvwxyz12/content.js",
              headers: [],
            },
          },
        ],
      },
    });
    const result = parseHar(har);
    expect(result.hostnames).toEqual([]);
  });
});
