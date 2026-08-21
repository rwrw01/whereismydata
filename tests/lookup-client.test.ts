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
          {
            hostname: "example.com",
            asn: 15169,
            org_name: "Google LLC",
            org_country: "US",
          },
        ],
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const results = await lookupHostnames("https://api.example.invalid", [
      "example.com",
    ]);

    expect(results).toEqual([
      {
        hostname: "example.com",
        asn: 15169,
        orgName: "Google LLC",
        orgCountry: "US",
      },
    ]);
    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.invalid/lookup",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ hostnames: ["example.com"] }),
      }),
    );
  });

  it("splits requests into batches of at most 200 hostnames", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ results: [] }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const hostnames = Array.from(
      { length: 250 },
      (_, i) => `h${i}.example.com`,
    );
    await lookupHostnames("https://api.example.invalid", hostnames);

    expect(fetchMock).toHaveBeenCalledTimes(2);
    const call0 = fetchMock.mock.calls[0];
    const call1 = fetchMock.mock.calls[1];
    if (!call0 || !call1) {
      throw new Error("Expected two fetch calls");
    }
    const firstBody = JSON.parse((call0[1] as RequestInit).body as string);
    const secondBody = JSON.parse((call1[1] as RequestInit).body as string);
    expect(firstBody.hostnames).toHaveLength(200);
    expect(secondBody.hostnames).toHaveLength(50);
  });

  it("throws LookupApiError on a non-ok response", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue({ ok: false, status: 503, json: async () => ({}) }),
    );

    await expect(
      lookupHostnames("https://api.example.invalid", ["a.com"]),
    ).rejects.toThrow(LookupApiError);
  });

  it("throws LookupApiError when the network request itself fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new TypeError("Failed to fetch")),
    );

    await expect(
      lookupHostnames("https://api.example.invalid", ["a.com"]),
    ).rejects.toThrow(LookupApiError);
  });
});
