import type { ReturnExecutionErrors } from "./return-posting.types";
export class ReturnPostingRequestError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
    public readonly code?: string,
    public readonly actualVersion?: number,
    public readonly fields: ReturnExecutionErrors = {
      rows: {},
      lines: {},
    },
  ) {
    super(message);
  }
}
