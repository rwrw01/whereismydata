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

async function lookupBatch(
  apiBaseUrl: string,
  hostnames: string[],
): Promise<LookupResult[]> {
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl}/lookup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ hostnames }),
    });
  } catch {
    throw new LookupApiError(
      "Kon geen verbinding maken met de lookup-service.",
    );
  }

  if (response.status === 429) {
    throw new LookupApiError(
      "Te veel scans vanaf dit IP-adres, probeer het later opnieuw.",
    );
  }

  if (!response.ok) {
    throw new LookupApiError(
      `Lookup-service gaf een fout terug (status ${response.status}).`,
    );
  }

  let data: ApiLookupResponse;
  try {
    data = (await response.json()) as ApiLookupResponse;
  } catch {
    throw new LookupApiError(
      "Lookup-service gaf een onverwacht antwoord terug.",
    );
  }

  if (!Array.isArray(data.results)) {
    throw new LookupApiError(
      "Lookup-service gaf een onverwacht antwoord terug.",
    );
  }

  return data.results.map((r) => ({
    hostname: r.hostname,
    asn: r.asn,
    orgName: r.org_name,
    orgCountry: r.org_country,
  }));
}

export async function lookupHostnames(
  apiBaseUrl: string,
  hostnames: string[],
): Promise<LookupResult[]> {
  const batches = chunk(hostnames, MAX_HOSTNAMES_PER_REQUEST);
  const batchResults = await Promise.all(
    batches.map((batch) => lookupBatch(apiBaseUrl, batch)),
  );
  return batchResults.flat();
}
