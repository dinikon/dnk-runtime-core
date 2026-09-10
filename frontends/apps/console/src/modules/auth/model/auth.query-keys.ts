export const authQueryKeys = {
  all: ["auth"] as const,
  currentUser: () => [...authQueryKeys.all, "current-user"] as const,
  tenant: () => [...authQueryKeys.all, "tenant"] as const,
};
