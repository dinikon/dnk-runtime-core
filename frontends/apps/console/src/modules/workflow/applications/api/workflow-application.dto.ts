/**
 * DTO — то, что приходит с API.
 */
export interface WorkflowApplicationListItemDto {
  id: string;
  created_at: string;
  kind: string;
  status: string;
  title: string;
  description: string | null;
  icon: string;
  icon_background: string;
}

export interface WorkflowApplicationListResponseDto {
  items: WorkflowApplicationListItemDto[];
  next_cursor: string | null;
}

export interface WorkflowApplicationResponseDto {
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

export interface CreateWorkflowApplicationRequestDto {
  title: string;
  description: string | null;
  icon: string;
  icon_background: string;
}
