type Scope = readonly (string | null)[];
export const funnelKeys = {
  options: (scope: Scope, modelKey: string) =>
    ["funnel-options", ...scope, modelKey] as const,
  list: (scope: Scope, modelKey: string, search: string, offset: number) =>
    ["funnels", ...scope, modelKey, search, offset] as const,
  detail: (scope: Scope, id: string) => ["funnel", ...scope, id] as const,
};
