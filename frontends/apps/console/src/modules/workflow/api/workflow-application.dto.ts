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

