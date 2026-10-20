import { isAxiosError } from "axios";
export class ChannelsApiError extends Error {
  constructor(
    public readonly status: number | undefined,
    public readonly code: string,
    public readonly issues: readonly { field: string; message: string }[] = [],
  ) {
    super(code);
    this.name = "ChannelsApiError";
  }
}
// Never keep Axios config/request bodies (credentials) in a mutation error.
export function normalizeApiError(error: unknown): ChannelsApiError {
  if (error instanceof ChannelsApiError) return error;
  if (!isAxiosError(error))
    return new ChannelsApiError(undefined, "transport_error");
  const detail: unknown = error.response?.data?.detail;
  if (
    error.response?.status === 422 &&
    detail &&
    typeof detail === "object" &&
    "code" in detail &&
    detail.code === "invalid_catalog_draft" &&
    "issues" in detail &&
    Array.isArray(detail.issues)
  ) {
    const issues = detail.issues
      .filter(
        (item: unknown): item is { field: string; message: string } =>
          !!item &&
          typeof item === "object" &&
          "field" in item &&
          typeof item.field === "string" &&
          "message" in item &&
          typeof item.message === "string",
      )
      .slice(0, 20)
      .map((item) => ({
        field: item.field.slice(0, 80),
        message: item.message.slice(0, 500),
      }));
    return new ChannelsApiError(422, "invalid_catalog_draft", issues);
  }
  return new ChannelsApiError(
    error.response?.status,
    typeof detail === "string" && /^[a-z_]+$/.test(detail)
      ? detail
      : "request_failed",
  );
}
