import { describe, expect, it } from "vitest";
import { isKnownTracker } from "../src/tracker-patterns";

describe("isKnownTracker", () => {
  it("matches known tracking-pixel and ad-network domains", () => {
    expect(isKnownTracker("stats.g.doubleclick.net")).toBe(true);
    expect(isKnownTracker("www.googletagmanager.com")).toBe(true);
    expect(isKnownTracker("www.google-analytics.com")).toBe(true);
    expect(isKnownTracker("connect.facebook.net")).toBe(true);
    expect(isKnownTracker("pixel.example.com")).toBe(true);
    expect(isKnownTracker("track.example.com")).toBe(true);
  });

  it("does not flag ordinary hostnames as trackers", () => {
    expect(isKnownTracker("bluedolphin.app")).toBe(false);
    expect(isKnownTracker("api-iam.intercom.io")).toBe(false);
    expect(isKnownTracker("fonts.gstatic.com")).toBe(false);
  });

  it("is case-insensitive", () => {
    expect(isKnownTracker("STATS.DOUBLECLICK.NET")).toBe(true);
  });
});
