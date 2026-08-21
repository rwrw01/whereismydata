export interface HostnameCount {
  host: string;
  count: number;
  cookieCount: number;
}

export interface HostnameEdge {
  parent: string;
  child: string;
}

export interface ParsedHar {
  hostnames: HostnameCount[];
  edges: HostnameEdge[];
  extensions: string[];
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
  cookieCount: number;
  asn: number | null;
  orgName: string | null;
  orgCountry: string | null;
  orgCountrySource: string | null;
}
