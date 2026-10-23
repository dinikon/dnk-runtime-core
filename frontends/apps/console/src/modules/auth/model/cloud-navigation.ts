// Pure URL helpers shared by the router and the login page.
export function requestsCloudLogin(provider: unknown): boolean {
  return provider === "cloud";
}

export function withoutAuthProvider(fullPath: string): string {
  const url = new URL(fullPath, "https://runtime.invalid");
  url.searchParams.delete("auth_provider");
  return `${url.pathname}${url.search}${url.hash}`;
}
