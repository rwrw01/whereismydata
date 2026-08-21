// Pure hostname-string classification — operates only on hostnames already
// extracted by har-parser.ts, never touches raw HAR fields. No whitelist
// implications: this reads nothing new, it only pattern-matches a value
// that is already sanitized and already leaves the browser.
const TRACKER_PATTERNS: RegExp[] = [
  /doubleclick\.net$/i,
  /googlesyndication\.com$/i,
  /googletagmanager\.com$/i,
  /google-analytics\.com$/i,
  /googleadservices\.com$/i,
  /adsystem\./i,
  /adservice\./i,
  /facebook\.(com|net)$/i,
  /hotjar\.com$/i,
  /^pixel\./i,
  /^track\./i,
  /^analytics\./i,
];

export function isKnownTracker(hostname: string): boolean {
  return TRACKER_PATTERNS.some((pattern) => pattern.test(hostname));
}
