import type { ReceiptIntakeErrors } from "./receipt-posting.types";
export class ReceiptPostingRequestError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
    public readonly code?: string,
    public readonly actualVersion?: number,
    public readonly fields: ReceiptIntakeErrors = { rows: {} },
  ) {
    super(message);
  }
}
