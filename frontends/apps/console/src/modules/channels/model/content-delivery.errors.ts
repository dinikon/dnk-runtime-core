import axios from "axios";
import { representationIssueMessage } from "./representation.errors";
import { contentDeliveryIssueLabel } from "./content-delivery.labels";

export function contentDeliveryIssue(code: string): string {
  return contentDeliveryIssueLabel(code) ?? representationIssueMessage(code);
}

export function contentDeliveryError(error: unknown): string {
  const code = axios.isAxiosError(error)
    ? error.response?.data?.detail?.code
    : undefined;
  return typeof code === "string"
    ? contentDeliveryIssue(code)
    : "Не удалось получить результат. Перечитайте состояние перед повторным запуском.";
}
