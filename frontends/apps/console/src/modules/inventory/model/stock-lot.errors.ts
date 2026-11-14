import type { StockLotErrors } from "./stock-lot.types.ts";
export class StockLotRequestError extends Error {
  constructor(
    message: string,
    readonly status: number | null,
    readonly fields: StockLotErrors = {},
  ) {
    super(message);
    this.name = "StockLotRequestError";
  }
  get uncertain(): boolean {
    return this.status === null || this.status >= 500 || this.status === 408;
  }
}
export function retryStockLots(count: number, error: Error): boolean {
  return (
    count < 1 &&
    !(
      error instanceof StockLotRequestError &&
      error.status !== null &&
      error.status >= 400 &&
      error.status < 500
    )
  );
}
