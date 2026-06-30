export const workflowApplicationQueryKeys = {
  all: ["console-workflows"] as const,

  applications: () =>
    [...workflowApplicationQueryKeys.all, "applications"] as const,

  applicationsList: (params: { limit: number }) =>
    [
      ...workflowApplicationQueryKeys.applications(),
      {
        limit: params.limit,
      },
    ] as const,
};

export type WorkflowApplicationsQueryKey = ReturnType<
  typeof workflowApplicationQueryKeys.applicationsList
>;
