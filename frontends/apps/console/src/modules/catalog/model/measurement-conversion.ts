import type { WeightUnit, LengthUnit } from "../api/catalog.dto";

/** Пересчитывает десятичную строку без промежуточного floating point. */
export function convertMeasurement(
  value: string,
  from: WeightUnit | LengthUnit,
  to: WeightUnit | LengthUnit,
): string | null {
  const match = /^([+-]?)(\d*)(?:\.(\d*))?(?:[eE]([+-]?\d+))?$/.exec(
    value.trim(),
  );
  if (!match || !(match[2] || match[3])) return null;
  const powers = { g: 0, kg: 3, cm: 1, m: 3 };
  const shift = Number(match[4] ?? 0) + powers[from] - powers[to];
  if (!Number.isSafeInteger(shift) || Math.abs(shift) > 1000) return null;
  const digits = (match[2] ?? "") + (match[3] ?? "");
  const point = (match[2]?.length ?? 0) + shift;
  const expanded =
    point <= 0
      ? "0." + "0".repeat(-point) + digits
      : point >= digits.length
        ? digits + "0".repeat(point - digits.length)
        : digits.slice(0, point) + "." + digits.slice(point);
  const [whole, fraction = ""] = expanded.split(".");
  const integer = whole!.replace(/^0+(?=\d)/, "") || "0";
  const decimal = fraction.replace(/0+$/, "");
  return (
    (match[1] === "-" && /[1-9]/.test(digits) ? "-" : "") +
    integer +
    (decimal ? "." + decimal : "")
  );
}
