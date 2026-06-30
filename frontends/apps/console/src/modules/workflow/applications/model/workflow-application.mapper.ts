import {
  type WorkflowApplicationListItemDto,
  type WorkflowApplicationListResponseDto,
} from "@/modules/workflow/applications/api/workflow-application.dto.ts";
import {
  type WorkflowApplicationListItem,
  type WorkflowApplicationListResponse,
} from "@/modules/workflow/applications/model/workflow-application.types.ts";

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
