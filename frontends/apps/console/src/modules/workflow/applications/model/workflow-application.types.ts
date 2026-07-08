export interface WorkflowApplicationListItem {
  id: string;
  createdAt: string;
  kind: string;
  status: string;
  title: string;
  description: string | null;
  icon: string;
  iconBackground: string;
}

export interface WorkflowApplicationListResponse {
  items: WorkflowApplicationListItem[];
  nextCursor: string | null;
}

export interface WorkflowApplicationMutationPayload {
  title: string;
  description: string | null;
  icon: string;
  iconBackground: string;
}

export type CreateWorkflowApplicationPayload =
  WorkflowApplicationMutationPayload;

export type UpdateWorkflowApplicationPayload =
  WorkflowApplicationMutationPayload & {
    id: string;
  };

export type WorkflowCursor = string | null;
