import type { WriteOffExecutionErrors } from "./write-off-posting.types";
export class WriteOffPostingRequestError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
    public readonly code?: string,
    public readonly actualVersion?: number,
    public readonly fields: WriteOffExecutionErrors = { rows: {}, lines: {} },
  ) {
    super(message);
  }
}
