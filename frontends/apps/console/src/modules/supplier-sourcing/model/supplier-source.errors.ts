import type { SourceFieldErrors } from "./supplier-source.types";
export class SupplierSourceRequestError extends Error {
  constructor(
    message: string,
    public readonly status: number | undefined,
    public readonly fields: SourceFieldErrors = {},
  ) {
    super(message);
  }
  get uncertain(): boolean {
    return this.status === undefined || this.status >= 500;
  }
}
