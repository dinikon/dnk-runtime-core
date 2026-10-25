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
  return value === undefined ? value : (JSON.parse(JSON.stringify(value)) as T);
}

/** Acknowledges only submitted fields, including server IDs and normalized row values. */
export function rebaseSavedSale(
  current: SaleDraft,
  sent: SaleDraft,
  saved: SaleDraft,
  lineIds: Record<string, string>,
): SaleDraft {
  const next = cloneSaleValue(current);
  for (const key of Object.keys(saved) as (keyof SaleDraft)[])
    if (
      key !== "items" &&
      key !== "points" &&
      JSON.stringify(current[key]) === JSON.stringify(sent[key])
    )
      Object.assign(next, { [key]: cloneSaleValue(saved[key]) });
  next.basketRevision = saved.basketRevision;
  next.items = current.items.map((row) => {
    const original = sent.items.find(
      (value) =>
        value.clientLineKey === row.clientLineKey ||
        (!!row.id && value.id === row.id),
    );
    const id = row.id ?? lineIds[row.clientLineKey];
    const persisted = saved.items.find((value) => value.id === id);
    if (!original || !persisted) return cloneSaleValue(row);
    const result = {
      ...cloneSaleValue(row),
      id,
      lineTotal: persisted.lineTotal,
    };
    for (const key of [
      "name",
      "kind",
      "quantity",
      "unitPrice",
      "unit",
      "catalogItemId",
      "sku",
      "customFields",
    ] as const)
      if (JSON.stringify(row[key]) === JSON.stringify(original[key]))
        Object.assign(result, { [key]: cloneSaleValue(persisted[key]) });
    return result;
  });
  if (JSON.stringify(current.points) === JSON.stringify(sent.points))
    next.points = cloneSaleValue(saved.points);
  else
    for (const group of ["phones", "emails"] as const)
      next.points[group] = next.points[group].map((point) => {
        const match = saved.points[group].find(
          (value) =>
            value.bindingId === point.bindingId || value.value === point.value,
        );
        return match
          ? {
              ...point,
              bindingId: match.bindingId,
              contactPointId: match.contactPointId,
            }
          : point;
      });
  return next;
}

/** Local rendering keys and derived totals do not make a form unsaved. */
function canonicalFormValue(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(canonicalFormValue);
  if (value && typeof value === "object")
    return Object.fromEntries(
      Object.entries(value)
        .filter(([, item]) => item !== undefined)
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([key, item]) => [key, canonicalFormValue(item)]),
    );
  return value;
}
export function saleDraftFingerprint(value: SaleDraft): string {
  return JSON.stringify(
    canonicalFormValue({
      ...value,
      items: value.items.map((item) => ({
        ...item,
        clientLineKey: undefined,
        lineTotal: undefined,
      })),
      points: {
        phones: value.points.phones.map((point) => ({
          ...point,
          clientKey: undefined,
        })),
        emails: value.points.emails.map((point) => ({
          ...point,
          clientKey: undefined,
        })),
      },
    }),
  );
}
