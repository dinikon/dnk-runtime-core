import { isAxiosError } from "axios";
import { FeedRequestError, type FeedRequestIssue } from "../model/feed-request-error";

export async function feedRequest<T>(run: () => Promise<T>): Promise<T> {
  try {
    return await run();
  } catch (error: unknown) {
    if (!isAxiosError(error)) throw error;
    const detail: unknown = error.response?.data?.detail;
    const issues: FeedRequestIssue[] = [];
    if (Array.isArray(detail))
      for (const issue of detail) {
        if (typeof issue !== "object" || !issue || !Array.isArray(issue.loc))
          continue;
        issues.push({
          code: "SCHEMA_INVALID",
          message: "Проверьте значение и тип настройки.",
          path: issue.loc
            .filter(
              (p: unknown) => typeof p === "string" || typeof p === "number",
            )
            .filter((p: string | number) => p !== "body"),
        });
      }
    else if (
      detail &&
      typeof detail === "object" &&
      "message" in detail &&
      typeof detail.message === "string"
    ) {
      const d = detail as Record<string, unknown>;
      issues.push({
        code: typeof d.code === "string" ? d.code : "SCHEMA_INVALID",
        message: detail.message,
        fieldId: typeof d.field_id === "string" ? d.field_id : undefined,
        path: Array.isArray(d.path)
          ? d.path.filter(
              (p: unknown) => typeof p === "string" || typeof p === "number",
            )
          : [],
      });
    }
    throw new FeedRequestError(error.response?.status, issues);
  }
}
