import type { ReturnErrors } from "./return.types";
export class ReturnRequestError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
    public readonly fields: ReturnErrors = { lineFields: {} },
    public readonly conflict?: {
      code: string;
      expectedVersion?: number;
      actualVersion?: number;
    },
  ) {
    super(message);
  }
}
