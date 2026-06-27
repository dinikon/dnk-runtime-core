import { httpClient } from "@/app/providers/http";

import type { CreateWorkflowPayload, WorkflowApplication } from "./types";

export const workflowAppApi = {
  createWorkflow: async (payload: CreateWorkflowPayload) =>
    (await httpClient.post<WorkflowApplication>("/console/workflows", payload)).data,
};
