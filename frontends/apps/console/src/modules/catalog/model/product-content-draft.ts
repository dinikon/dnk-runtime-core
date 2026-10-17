/** Полный набор контента одной locale; визуальные редакторы не владеют копиями. */
export function changeProductContent(
  values: Record<string, string>,
  code: "name" | "short_desc" | "desc",
  value: string | undefined,
): Record<string, string> {
  const next = { ...values };
  if (value === undefined) delete next[code];
  else next[code] = value;
  return next;
}
