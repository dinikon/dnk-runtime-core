import type { InternalMoveErrors } from "./internal-move.types";
export class InternalMoveRequestError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
    public readonly fields: InternalMoveErrors = { lineFields: {} },
    public readonly conflict?: {
      code: string;
      expectedVersion?: number;
      actualVersion?: number;
    },
  ) {
    super(message);
  }
}
