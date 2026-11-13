import type { ItemPackagingErrors } from "./item-packaging.types.ts";
export class ItemPackagingRequestError extends Error {
  constructor(
    message: string,
    readonly status: number | null,
    readonly fields: ItemPackagingErrors = {},
  ) {
    super(message);
    this.name = "ItemPackagingRequestError";
  }
  get uncertain(): boolean {
    return this.status === null || this.status >= 500 || this.status === 408;
  }
}
export function retryItemPackagings(count: number, error: Error): boolean {
  return (
    count < 1 &&
    !(
      error instanceof ItemPackagingRequestError &&
      error.status !== null &&
      error.status >= 400 &&
      error.status < 500
    )
  );
}
