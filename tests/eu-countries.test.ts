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
