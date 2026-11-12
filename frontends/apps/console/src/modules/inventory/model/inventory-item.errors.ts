export class InventoryItemsRequestError extends Error {
  constructor(
    message: string,
    readonly status: number | null,
  ) {
    super(message);
    this.name = "InventoryItemsRequestError";
  }
}

export function retryInventoryItems(
  failureCount: number,
  error: Error,
): boolean {
  return (
    failureCount < 1 &&
    !(
      error instanceof InventoryItemsRequestError &&
      error.status !== null &&
      error.status >= 400 &&
      error.status < 500
    )
  );
}
