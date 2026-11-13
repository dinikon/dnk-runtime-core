import type {
  PackagingTypeEditValues,
  PackagingTypeChanges,
} from "./packaging-type.types.ts";
export function packagingTypeSnapshot(
  value: PackagingTypeEditValues,
): PackagingTypeEditValues {
  return { code: value.code, name: value.name, isActive: value.isActive };
}
export function packagingTypeChanges(
  value: PackagingTypeEditValues,
  baseline: PackagingTypeEditValues,
): PackagingTypeChanges {
  const changes: PackagingTypeChanges = {};
  if (value.code !== baseline.code) changes.code = value.code;
  if (value.name !== baseline.name) changes.name = value.name;
  if (value.isActive !== baseline.isActive) changes.isActive = value.isActive;
  return changes;
}
export class PackagingTypeDraft {
  values: PackagingTypeEditValues | null = null;
  private baseline: PackagingTypeEditValues | null = null;
  get changes(): PackagingTypeChanges {
    return this.values && this.baseline
      ? packagingTypeChanges(this.values, this.baseline)
      : {};
  }
  get dirty(): boolean {
    return Object.keys(this.changes).length > 0;
  }
  receive(value: PackagingTypeEditValues): void {
    if (!this.dirty) this.reset(value);
  }
  change(value: PackagingTypeEditValues): void {
    this.values = packagingTypeSnapshot(value);
  }
  reset(value: PackagingTypeEditValues): void {
    this.values = packagingTypeSnapshot(value);
    this.baseline = packagingTypeSnapshot(value);
  }
  clear(): void {
    this.values = null;
    this.baseline = null;
  }
  acknowledge(
    sent: PackagingTypeEditValues,
    result: PackagingTypeEditValues,
  ): void {
    if (!this.values) return;
    const current = this.values;
    this.values = {
      code: current.code === sent.code ? result.code : current.code,
      name: current.name === sent.name ? result.name : current.name,
      isActive:
        current.isActive === sent.isActive ? result.isActive : current.isActive,
    };
    this.baseline = packagingTypeSnapshot(result);
  }
}
