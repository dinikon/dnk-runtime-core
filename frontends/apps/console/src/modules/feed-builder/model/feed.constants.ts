import type { FeedStatus } from "./feed.types";
export const feedStatuses: Record<FeedStatus, string> = {
  DRAFT: "Черновик",
  ACTIVE: "Активен",
  PAUSED: "Приостановлен",
  ARCHIVED: "В архиве",
};
