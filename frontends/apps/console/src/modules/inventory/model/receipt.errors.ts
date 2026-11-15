import type { ReceiptErrors } from "./receipt.types";
export class ReceiptRequestError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
    public readonly fields: ReceiptErrors = { lineFields: {} },
  ) {
    super(message);
  }
}
