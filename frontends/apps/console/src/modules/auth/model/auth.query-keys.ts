export const authQueryKeys = {
  all: ["auth"] as const,
  currentUser: () => [...authQueryKeys.all, "current-user"] as const,
  tenant: () => [...authQueryKeys.all, "tenant"] as const,
  cloudStatus: (tenantId: string | null) =>
    [...authQueryKeys.all, "cloud-status", tenantId] as const,
};
