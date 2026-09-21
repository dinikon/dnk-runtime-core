/** Format an exact decimal string; precision and rounding are explicit. */
export function formatDecimal(
  value: string,
  precision?: number | null,
  rounding = "ROUND_HALF_UP",
): string {
  const match = /^(-?)(\d+)(?:\.(\d+))?$/.exec(value);
  if (!match) return value;
  let [, sign, integer, fraction = ""] = match;
  if (precision != null && fraction.length > precision) {
    const kept = fraction.slice(0, precision);
    const tail = fraction.slice(precision);
    let coefficient = BigInt(integer + kept);
    const nonzero = /[1-9]/.test(tail);
    const halfway = tail[0] === "5" && !/[1-9]/.test(tail.slice(1));
    const above = tail[0] > "5" || (tail[0] === "5" && !halfway);
    const increment =
      rounding === "ROUND_UP"
        ? nonzero
        : rounding === "ROUND_DOWN"
          ? false
          : rounding === "ROUND_HALF_EVEN"
            ? above || (halfway && coefficient % 2n !== 0n)
            : tail[0] >= "5";
    if (increment) coefficient += 1n;
    const digits = coefficient.toString().padStart(precision + 1, "0");
    integer = precision ? digits.slice(0, -precision) : digits;
    fraction = precision ? digits.slice(-precision) : "";
  } else if (precision != null) {
    fraction = fraction.padEnd(precision, "0");
  }
  if (!/[1-9]/.test(integer + fraction)) sign = "";
  return (
    sign +
    integer.replace(/\B(?=(\d{3})+(?!\d))/g, "\u00a0") +
    (fraction ? "," + fraction : "")
  );
}

export function formatMoney(value: string | null, currency = "UAH"): string {
  return value === null ? "—" : `${formatDecimal(value)} ${currency}`;
}
