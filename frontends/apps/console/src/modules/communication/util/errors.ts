import { isAxiosError } from "axios";

export function apiErrorMessage(error: unknown): string {
  if (isAxiosError(error)) {
    const detail = error.response?.data?.detail;

    if (typeof detail === "string") {
      return detail;
    }

    if (detail !== undefined) {
      return JSON.stringify(detail);
    }

    return error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Unexpected error.";
}
