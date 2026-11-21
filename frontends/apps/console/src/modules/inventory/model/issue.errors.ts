import type { IssueErrors } from "./issue.types";
export class IssueRequestError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
    public readonly fields: IssueErrors = { lineFields: {} },
    public readonly conflict?: {
      code: string;
      expectedVersion?: number;
      actualVersion?: number;
    },
  ) {
    super(message);
  }
}
