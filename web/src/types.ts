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
  orgCountrySource: string | null;
}

export interface ResultRow {
  hostname: string;
  count: number;
  asn: number | null;
  orgName: string | null;
  orgCountry: string | null;
  orgCountrySource: string | null;
}
