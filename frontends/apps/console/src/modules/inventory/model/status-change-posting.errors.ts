import type { StatusChangeExecutionErrors } from "./status-change-posting.types";
export class StatusChangePostingRequestError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
    public readonly code?: string,
    public readonly actualVersion?: number,
    public readonly fields: StatusChangeExecutionErrors = {
      rows: {},
      lines: {},
    },
  ) {
    super(message);
  }
}
