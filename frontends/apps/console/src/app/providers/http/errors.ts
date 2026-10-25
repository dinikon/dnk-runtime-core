import axios from "axios";

export function getApiErrorMessage(error: unknown, fallback: string): string {
  if (!axios.isAxiosError(error)) {
    return fallback;
  }

  const detail = error.response?.data;

  if (typeof detail === "string" && detail.trim().length > 0) {
    return detail;
  }

  if (
    detail &&
    typeof detail === "object" &&
    "detail" in detail &&
    typeof detail.detail === "string"
  ) {
    return detail.detail;
  }

  if (
    detail &&
    typeof detail === "object" &&
    "detail" in detail &&
    detail.detail &&
    typeof detail.detail === "object" &&
    "message" in detail.detail &&
    typeof detail.detail.message === "string" &&
    detail.detail.message.trim().length > 0
  ) {
    return detail.detail.message;
  }

  return fallback;
}

export function getApiErrorStatus(error: unknown): number | null {
  return axios.isAxiosError(error) ? (error.response?.status ?? null) : null;
}
