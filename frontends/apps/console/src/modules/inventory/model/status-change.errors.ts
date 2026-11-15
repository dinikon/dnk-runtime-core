import type { StatusChangeErrors } from "./status-change.types";
export class StatusChangeRequestError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
    public readonly fields: StatusChangeErrors = { lineFields: {} },
    public readonly conflict?: {
      code: string;
      expectedVersion?: number;
      actualVersion?: number;
    },
  ) {
    super(message);
  }
}
