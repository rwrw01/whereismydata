import { renderExtensionsList } from "./extensions-list";
import { InvalidHarError, parseHar } from "./har-parser";
import { renderHostnameTree } from "./hostname-tree";
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

const setStatus = (message: string): void => {
  statusEl.textContent = message;
};

const handleFile = async (file: File): Promise<void> => {
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
    setStatus(
      `${parsed.hostnames.length} hostnamen gevonden, leveranciers opzoeken...`,
    );

    const lookups = await lookupHostnames(
      LOOKUP_API_URL,
      parsed.hostnames.map((h) => h.host),
    );
    const lookupByHost = new Map(lookups.map((l) => [l.hostname, l]));

    const rows: ResultRow[] = parsed.hostnames.map((h) => {
      const lookup = lookupByHost.get(h.host);
      return {
        hostname: h.host,
        count: h.count,
        cookieCount: h.cookieCount,
        asn: lookup?.asn ?? null,
        orgName: lookup?.orgName ?? null,
        orgCountry: lookup?.orgCountry ?? null,
        orgCountrySource: lookup?.orgCountrySource ?? null,
      };
    });

    setStatus(`${rows.length} hostnamen geanalyseerd.`);

    const tableSection = document.createElement("div");
    renderResultsTable(tableSection, rows);

    const treeSection = document.createElement("div");
    renderHostnameTree(
      treeSection,
      parsed.edges,
      parsed.hostnames.map((h) => h.host),
    );

    const extensionsSection = document.createElement("div");
    renderExtensionsList(extensionsSection, parsed.extensions);

    resultsEl.append(tableSection, treeSection, extensionsSection);
  } catch (error) {
    if (error instanceof InvalidHarError || error instanceof LookupApiError) {
      setStatus(error.message);
      return;
    }
    setStatus("Er ging iets onverwachts mis.");
  }
};

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
