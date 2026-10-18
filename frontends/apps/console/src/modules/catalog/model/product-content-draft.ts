/** Полный набор контента одной locale; визуальные редакторы не владеют копиями. */
export function changeProductContent(
  values: Record<string, string>,
  code: "title" | "body",
  value: string | undefined,
): Record<string, string> {
  const next = { ...values };
  if (value === undefined) delete next[code];
  else next[code] = value;
  return next;
}
