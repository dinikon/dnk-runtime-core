import { isAxiosError } from "axios";
export class ChannelsApiError extends Error {
  constructor(
    public readonly status: number | undefined,
    public readonly code: string,
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
  return new ChannelsApiError(
    error.response?.status,
    typeof detail === "string" && /^[a-z_]+$/.test(detail)
      ? detail
      : "request_failed",
  );
}
