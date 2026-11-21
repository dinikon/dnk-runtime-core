import type { StockSerialErrors } from "./stock-serial.types.ts";
export class StockSerialRequestError extends Error {
  constructor(
    message: string,
    readonly status: number | null,
    readonly fields: StockSerialErrors = {},
  ) {
    super(message);
    this.name = "StockSerialRequestError";
  }
  get uncertain(): boolean {
    return this.status === null || this.status >= 500 || this.status === 408;
  }
}
export function retryStockSerials(count: number, error: Error): boolean {
  return (
    count < 1 &&
    !(
      error instanceof StockSerialRequestError &&
      error.status !== null &&
      error.status >= 400 &&
      error.status < 500
    )
  );
}
