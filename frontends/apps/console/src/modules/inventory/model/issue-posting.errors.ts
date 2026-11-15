import type { IssueExecutionErrors } from "./issue-posting.types";
export class IssuePostingRequestError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
    public readonly code?: string,
    public readonly actualVersion?: number,
    public readonly fields: IssueExecutionErrors = { rows: {}, lines: {} },
  ) {
    super(message);
  }
}
