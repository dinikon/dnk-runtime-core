import {
    WorkflowApplicationListItemDto,
    WorkflowApplicationListResponseDto
} from "@/modules/workflow/api/workflow-application.dto.ts";
import {
    WorkflowApplicationListItem,
    WorkflowApplicationListResponse
} from "@/modules/workflow/model/workflow-application.types.ts";


export function mapWorkflowApplicationListItem(
  dto: WorkflowApplicationListItemDto,
): WorkflowApplicationListItem {
  return {
    id: dto.id,
    createdAt: dto.created_at,
    kind: dto.kind,
    status: dto.status,
    title: dto.title,
    description: dto.description,
    icon: dto.icon,
    iconBackground: dto.icon_background,
  };
}

export function mapWorkflowApplicationList(
  dto: WorkflowApplicationListResponseDto,
): WorkflowApplicationListResponse {
  return {
    items: dto.items.map(mapWorkflowApplicationListItem),
    nextCursor: dto.next_cursor,
  };
}