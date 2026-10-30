import type { PublicationCard } from "./publication.types";
import type { BindingPosition } from "./bindings/binding.types";

interface Decimal {
  units: bigint;
  scale: number;
}
function decimal(value: string): Decimal | null {
  if (value.length > 1000) return null;
  const match = /^(-?)(\d+)(?:\.(\d+))?(?:[eE]([+-]?\d+))?$/.exec(value);
  if (!match) return null;
  const exponent = Number(match[4] ?? 0);
  if (!Number.isInteger(exponent) || Math.abs(exponent) > 1000) return null;
  let units = BigInt(match[2]! + (match[3] ?? "")) * (match[1] ? -1n : 1n);
  const scale = (match[3]?.length ?? 0) - exponent;
  if (scale < 0) units *= 10n ** BigInt(-scale);
  return { units, scale: Math.max(0, scale) };
}
function atScale(value: Decimal, scale: number): bigint {
  return value.units * 10n ** BigInt(scale - value.scale);
}
function format(value: Decimal): string {
  const digits = (value.units < 0n ? -value.units : value.units)
    .toString()
    .padStart(value.scale + 1, "0");
  const whole = value.scale ? digits.slice(0, -value.scale) : digits;
  const fraction = value.scale
    ? digits.slice(-value.scale).replace(/0+$/, "")
    : "";
  return (
    (value.units < 0n ? "-" : "") + whole + (fraction ? "." + fraction : "")
  );
}

export function publicationPrice(card: PublicationCard): string {
  if (card.minPrice === null) {
    const currencies = new Set(
      card.items.filter((p) => p.price !== null).map((p) => p.currency),
    );
    return currencies.size > 1 ? "Разные валюты" : "Не получена";
  }
  const max = card.maxPrice ?? card.minPrice;
  return (
    card.minPrice +
    (max !== card.minPrice ? "–" + max : "") +
    " " +
    (card.currency ?? "")
  );
}

export function bindingPublicationPrice(
  positions: readonly BindingPosition[],
): string {
  const priced = positions.filter(
    (p) => p.kind !== "variable" && p.price !== null,
  );
  if (!priced.length) return "Не получена";
  const currencies = new Set(priced.map((p) => p.currency));
  if (currencies.size > 1) return "Разные валюты";
  const values = priced.map((p) => decimal(p.price!));
  if (values.some((v) => !v)) return "Не получена";
  const decimals = values as Decimal[];
  const scale = Math.max(...decimals.map((v) => v.scale));
  const sorted = decimals.sort((a, b) =>
    atScale(a, scale) < atScale(b, scale)
      ? -1
      : atScale(a, scale) > atScale(b, scale)
        ? 1
        : 0,
  );
  const min = format(sorted[0]!),
    max = format(sorted.at(-1)!);
  return (
    min +
    (min !== max ? "–" + max : "") +
    (priced[0]?.currency ? " " + priced[0].currency : "")
  );
}

interface StockPosition {
  id: string;
  kind: string;
  quantity: string | null;
  source: string;
}
function stock(positions: readonly StockPosition[]): string {
  const sources = new Map<string, Decimal | null>();
  for (const position of positions.filter((p) => p.kind !== "variable")) {
    const key = position.source || position.id;
    const value =
      position.quantity === null ? null : decimal(position.quantity);
    if (!sources.has(key)) sources.set(key, value);
    else {
      const before = sources.get(key);
      if (!before || !value || format(before) !== format(value))
        sources.set(key, null);
    }
  }
  const values = [...sources.values()];
  if (!values.length || values.every((v) => v === null)) return "Не получен";
  if (values.some((v) => v === null)) return "Частично получен";
  const decimals = values as Decimal[],
    scale = Math.max(...decimals.map((v) => v.scale));
  return format({
    units: decimals.reduce((sum, v) => sum + atScale(v, scale), 0n),
    scale,
  });
}
export function publicationStock(card: PublicationCard): string {
  return stock(
    card.items.map((p) => ({ ...p, source: p.stockSourcePublicationId })),
  );
}
export function bindingPublicationStock(
  positions: readonly BindingPosition[],
): string {
  return stock(positions.map((p) => ({ ...p, source: p.stockSourceId })));
}
