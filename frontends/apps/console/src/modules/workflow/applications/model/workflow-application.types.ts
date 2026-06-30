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

export type WorkflowCursor = string | null;
