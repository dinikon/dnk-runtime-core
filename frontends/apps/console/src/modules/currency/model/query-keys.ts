export const currencyQueryKeys = {
  all: ["currency"] as const,
  settings: ["currency", "settings"] as const,
  directory: ["currency", "directory"] as const,
  sources: ["currency", "sources"] as const,
  rates: (provider: string, offset: number) =>
    ["currency", "rates", provider, offset] as const,
};
