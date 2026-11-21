import type {
  StockLot,
  StockLotDatesValues,
  StockLotDatesChanges,
} from "./stock-lot.types.ts";
export function stockLotDatesValues(lot: StockLot): StockLotDatesValues {
  return {
    manufacturedOn: lot.manufacturedOn ?? "",
    expiresOn: lot.expiresOn ?? "",
  };
}
export function stockLotDatesChanges(
  value: StockLotDatesValues,
  baseline: StockLotDatesValues,
): StockLotDatesChanges {
  const result: StockLotDatesChanges = {};
  if (value.manufacturedOn !== baseline.manufacturedOn)
    result.manufacturedOn = value.manufacturedOn;
  if (value.expiresOn !== baseline.expiresOn)
    result.expiresOn = value.expiresOn;
  return result;
}
export class StockLotDatesDraft {
  values: StockLotDatesValues | null = null;
  private baseline: StockLotDatesValues | null = null;
  get changes(): StockLotDatesChanges {
    return this.values && this.baseline
      ? stockLotDatesChanges(this.values, this.baseline)
      : {};
  }
  get dirty(): boolean {
    return Object.keys(this.changes).length > 0;
  }
  receive(value: StockLotDatesValues): void {
    if (!this.dirty) this.reset(value);
  }
  change(value: StockLotDatesValues): void {
    this.values = {
      manufacturedOn: value.manufacturedOn,
      expiresOn: value.expiresOn,
    };
  }
  reset(value: StockLotDatesValues): void {
    this.change(value);
    this.baseline = {
      manufacturedOn: value.manufacturedOn,
      expiresOn: value.expiresOn,
    };
  }
  clear(): void {
    this.values = null;
    this.baseline = null;
  }
  rebase(value: StockLotDatesValues): void {
    if (!this.values) this.change(value);
    this.baseline = { ...value };
  }
  acknowledge(sent: StockLotDatesValues, result: StockLotDatesValues): void {
    if (!this.values) return;
    this.values = {
      manufacturedOn:
        this.values.manufacturedOn === sent.manufacturedOn
          ? result.manufacturedOn
          : this.values.manufacturedOn,
      expiresOn:
        this.values.expiresOn === sent.expiresOn
          ? result.expiresOn
          : this.values.expiresOn,
    };
    this.baseline = { ...result };
  }
}
