import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";

const dirtyHarPath = fileURLToPath(
  new URL("../tests/fixtures/dirty-sample.har", import.meta.url),
);

test("uploading a HAR file shows a results table with leverancier and zetel", async ({
  page,
}) => {
  await page.goto("/");

  const fileInput = page.locator("#file-input");
  await fileInput.setInputFiles(path.resolve(dirtyHarPath));

  await expect(page.locator("#status")).toContainText(
    "hostnamen geanalyseerd",
    {
      timeout: 15_000,
    },
  );

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
    dataTransfer.items.add(
      new File(["not json"], "broken.har", { type: "application/json" }),
    );
    if (input) input.files = dataTransfer.files;
    input?.dispatchEvent(new Event("change", { bubbles: true }));
  });

  await expect(page.locator("#status")).toContainText(
    "Kon HAR-bestand niet lezen",
  );
});
