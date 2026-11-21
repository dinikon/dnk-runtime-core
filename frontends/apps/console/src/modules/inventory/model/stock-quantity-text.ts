export function quantityText(value: string): string {
  const text = value.trim().replace(",", ".");
  const match = /^(\d+)(?:\.(\d+))?[eE]([+-]?\d{1,3})$/.exec(text);
  if (!match) return text;
  const whole = match[1] ?? "0",
    fraction = match[2] ?? "";
  // В число переводится только ограниченный показатель степени, а не количество.
  const point = whole.length + Number.parseInt(match[3] ?? "0", 10);
  const digits = whole + fraction;
  if (point <= 0) return `0.${"0".repeat(-point)}${digits}`;
  if (point >= digits.length) return digits + "0".repeat(point - digits.length);
  return `${digits.slice(0, point)}.${digits.slice(point)}`;
}
function quantityParts(
  value: string,
): { coefficient: bigint; scale: number } | null {
  const q = quantityText(value);
  if (q.length > 128 || !/^\d+(?:\.\d+)?$/.test(q)) return null;
  const [whole = "0", fraction = ""] = q.split(".");
  return { coefficient: BigInt(whole + fraction), scale: fraction.length };
}
export function compareQuantities(left: string, right: string): number {
  const a = quantityParts(left),
    b = quantityParts(right);
  if (!a || !b) return 0;
  const scale = Math.max(a.scale, b.scale);
  const x = a.coefficient * 10n ** BigInt(scale - a.scale),
    y = b.coefficient * 10n ** BigInt(scale - b.scale);
  return x > y ? 1 : x < y ? -1 : 0;
}
export function sumQuantities(values: readonly string[]): string | null {
  const parts = values.map(quantityParts);
  if (parts.some((part) => part === null)) return null;
  const scale = Math.max(0, ...parts.map((part) => part?.scale ?? 0));
  let sum = 0n;
  for (const part of parts)
    if (part) sum += part.coefficient * 10n ** BigInt(scale - part.scale);
  if (!scale) return String(sum);
  const digits = String(sum).padStart(scale + 1, "0");
  return `${digits.slice(0, -scale)}.${digits.slice(-scale)}`.replace(
    /\.?0+$/,
    "",
  );
}
