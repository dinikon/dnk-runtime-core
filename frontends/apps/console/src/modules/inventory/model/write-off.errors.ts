import type { WriteOffErrors } from "./write-off.types";
export class WriteOffRequestError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
    public readonly fields: WriteOffErrors = { lineFields: {} },
    public readonly conflict?: {
      code: string;
      expectedVersion?: number;
      actualVersion?: number;
    },
  ) {
    super(message);
  }
}
