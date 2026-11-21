import type { WarehouseDefaultStorageFieldErrors } from "./warehouse-default-storage.types.ts";

export class WarehouseDefaultStorageRequestError extends Error {
  constructor(
    message: string,
    readonly status: number | null,
    readonly fields: WarehouseDefaultStorageFieldErrors = {},
  ) {
    super(message);
    this.name = "WarehouseDefaultStorageRequestError";
  }

  get uncertain(): boolean {
    return this.status === null || this.status === 408 || this.status >= 500;
  }
}
