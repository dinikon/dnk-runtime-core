export const workflowQueryKeys = {
  all: ["workflow"] as const,
  applications: () => [...workflowQueryKeys.all, "applications"] as const,
};
