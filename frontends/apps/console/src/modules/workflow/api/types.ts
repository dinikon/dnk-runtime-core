export interface CreateWorkflowPayload {
  title: string;
  description: string | null;
  icon: string;
  icon_background: string;
}

export interface WorkflowApplication {
  id: string;
  created_at: string;
  updated_at: string;
  created_by: string | null;
  updated_by: string | null;
  kind: string;
  status: string;
  title: string;
  description: string | null;
  icon: string;
  icon_background: string;
  active_workflow_definition_id: string | null;
}
