export const workflowQueryKeys = {
  all: ["console-workflows"] as const,

  applications: () => [...workflowQueryKeys.all, "applications"] as const,

  applicationsList: (params: { limit: number }) =>
    [
      ...workflowQueryKeys.applications(),
      {
        limit: params.limit,
      },
    ] as const,
};

export type WorkflowApplicationsQueryKey = ReturnType<
  typeof workflowQueryKeys.applicationsList
>;
