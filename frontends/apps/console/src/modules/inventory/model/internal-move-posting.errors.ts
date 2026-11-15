import type { InternalMoveExecutionErrors } from "./internal-move-posting.types";
export class InternalMovePostingRequestError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
    public readonly code?: string,
    public readonly actualVersion?: number,
    public readonly fields: InternalMoveExecutionErrors = {
      rows: {},
      lines: {},
    },
  ) {
    super(message);
  }
}
