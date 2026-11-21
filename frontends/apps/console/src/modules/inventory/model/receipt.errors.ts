import type { ReceiptErrors } from "./receipt.types";
export class ReceiptRequestError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
    public readonly fields: ReceiptErrors = { lineFields: {} },
    public readonly conflict?: {
      code: string;
      expectedVersion?: number;
      actualVersion?: number;
    },
  ) {
    super(message);
  }
}
