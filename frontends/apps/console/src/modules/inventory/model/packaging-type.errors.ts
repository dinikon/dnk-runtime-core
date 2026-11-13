import type { PackagingTypeFieldErrors } from "./packaging-type.types.ts";
export class PackagingTypeRequestError extends Error {
  constructor(
    message: string,
    readonly status: number | null,
    readonly fields: PackagingTypeFieldErrors = {},
  ) {
    super(message);
    this.name = "PackagingTypeRequestError";
  }
  get uncertain(): boolean {
    return this.status === null || this.status >= 500 || this.status === 408;
  }
}
export function retryPackagingTypes(count: number, error: Error): boolean {
  return (
    count < 1 &&
    !(
      error instanceof PackagingTypeRequestError &&
      error.status !== null &&
      error.status >= 400 &&
      error.status < 500
    )
  );
}
