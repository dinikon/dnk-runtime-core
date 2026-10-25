import type { SaleDraft, SaleRecord, BasketLine } from "./sales.types";
export function emptySaleDraft(funnelId = "", currency = ""): SaleDraft {
  return {
    title: "",
    currency,
    funnelId,
    firstName: "",
    lastName: "",
    middleName: "",
    companyName: "",
    contactId: null,
    companyId: null,
    contactIds: [],
    companyIds: [],
    points: { phones: [], emails: [] },
    items: [],
  };
}
export function saleDraft(v: SaleRecord): SaleDraft {
  return {
    title: v.title,
    currency: v.basket.currency,
    funnelId: v.funnelId,
    firstName: v.firstName ?? "",
    lastName: v.lastName ?? "",
    middleName: v.middleName ?? "",
    companyName: v.companyName ?? "",
    contactId: v.contactId,
    companyId: v.companyId,
    contactIds: [...v.contactIds],
    companyIds: [...v.companyIds],
    points: cloneSaleValue(v.points),
    items: cloneSaleValue(v.basket.items),
    basketRevision: v.basket.revision,
  };
}
export function newBasketLine(): BasketLine {
  return {
    clientLineKey: crypto.randomUUID(),
    name: "",
    kind: "product",
    quantity: "1",
    unitPrice: "",
    unit: "шт.",
    catalogItemId: null,
    sku: null,
    customFields: {},
  };
}
function fixed(v: string): bigint {
  const s = v.trim().replace(",", ".");
  if (!/^\d{1,12}(?:\.\d{1,6})?$/.test(s))
    throw new Error("Введите число с точностью до 6 знаков.");
  const [a, b = ""] = s.split(".");
  return BigInt(a!) * 1000000n + BigInt(b.padEnd(6, "0"));
}
export function lineTotal(v: BasketLine): string {
  const q = fixed(v.quantity),
    p = fixed(v.unitPrice);
  if (q <= 0n) throw new Error("Количество должно быть больше нуля.");
  return centsText((q * p + 5000000000n) / 10000000000n);
}
function centsText(v: bigint): string {
  return (v / 100n).toString() + "." + (v % 100n).toString().padStart(2, "0");
}
export function basketPreview(items: BasketLine[]): string {
  let total = 0n;
  for (const i of items) {
    const s = lineTotal(i);
    total += BigInt(s.replace(".", ""));
  }
  return centsText(total);
}
export function validateSaleDraft(v: SaleDraft): string | null {
  if (!v.title.trim()) return "Укажите название.";
  if (!["USD", "EUR", "UAH"].includes(v.currency)) return "Выберите валюту.";
  if (v.items.length > 200) return "Допускается до 200 позиций.";
  for (const i of v.items) {
    if (!i.name.trim() || !i.unit.trim())
      return "Заполните название и единицу каждой позиции.";
    try {
      lineTotal(i);
    } catch (e) {
      return e instanceof Error ? e.message : "Проверьте количества и цены.";
    }
  }
  return null;
}

export function cloneSaleValue<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}
