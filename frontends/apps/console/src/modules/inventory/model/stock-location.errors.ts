import type { StockLocationFieldErrors } from "./stock-location.types.ts";
export class StockLocationRequestError extends Error {
  constructor(
    message: string,
    readonly status: number | null,
    readonly fields: StockLocationFieldErrors = {},
  ) {
    super(message);
    this.name = "StockLocationRequestError";
  }
  get uncertain(): boolean {
    return this.status === null || this.status >= 500 || this.status === 408;
  }
}
export function retryStockLocations(count: number, error: Error): boolean {
  return (
    count < 1 &&
    !(
      error instanceof StockLocationRequestError &&
      error.status !== null &&
      error.status >= 400 &&
      error.status < 500
    )
  );
}
export function stockLocationUnavailable(error: unknown): boolean {
  return (
    error instanceof StockLocationRequestError &&
    (error.status === 403 || error.status === 404)
  );
}
