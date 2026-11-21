import type { WarehouseFieldErrors } from "./warehouse.types.ts";
export class WarehouseRequestError extends Error {
  constructor(
    message: string,
    readonly status: number | null,
    readonly fields: WarehouseFieldErrors = {},
  ) {
    super(message);
    this.name = "WarehouseRequestError";
  }
  get uncertain(): boolean {
    return this.status === null || this.status >= 500 || this.status === 408;
  }
}
export function retryWarehouses(count: number, error: Error): boolean {
  return (
    count < 1 &&
    !(
      error instanceof WarehouseRequestError &&
      error.status !== null &&
      error.status >= 400 &&
      error.status < 500
    )
  );
}
