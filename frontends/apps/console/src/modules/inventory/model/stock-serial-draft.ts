import type {
  StockSerial,
  StockSerialValues,
  StockSerialChanges,
} from "./stock-serial.types.ts";
export function stockSerialValues(serial: StockSerial): StockSerialValues {
  return {
    number: serial.number,
    lotId: serial.lotId ?? "",
  };
}
export function stockSerialChanges(
  value: StockSerialValues,
  baseline: StockSerialValues,
): StockSerialChanges {
  const result: StockSerialChanges = {};
  if (value.number !== baseline.number) result.number = value.number;
  if (value.lotId !== baseline.lotId) result.lotId = value.lotId;
  return result;
}
export class StockSerialDraft {
  values: StockSerialValues | null = null;
  private baseline: StockSerialValues | null = null;
  get changes(): StockSerialChanges {
    return this.values && this.baseline
      ? stockSerialChanges(this.values, this.baseline)
      : {};
  }
  get dirty(): boolean {
    return Object.keys(this.changes).length > 0;
  }
  receive(value: StockSerialValues): void {
    if (!this.dirty) this.reset(value);
  }
  change(value: StockSerialValues): void {
    this.values = {
      number: value.number,
      lotId: value.lotId,
    };
  }
  reset(value: StockSerialValues): void {
    this.change(value);
    this.baseline = {
      number: value.number,
      lotId: value.lotId,
    };
  }
  clear(): void {
    this.values = null;
    this.baseline = null;
  }
  rebase(value: StockSerialValues): void {
    if (!this.values) this.change(value);
    this.baseline = { ...value };
  }
  acknowledge(sent: StockSerialValues, result: StockSerialValues): void {
    if (!this.values) return;
    this.values = {
      number:
        this.values.number === sent.number ? result.number : this.values.number,
      lotId:
        this.values.lotId === sent.lotId ? result.lotId : this.values.lotId,
    };
    this.baseline = { ...result };
  }
}
