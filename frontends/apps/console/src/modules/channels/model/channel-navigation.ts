/** Возврат разрешён только во внутренний список подключений. */
export function channelListReturnTo(value: unknown): string {
  if (
    typeof value !== "string" ||
    !value.startsWith("/") ||
    value.startsWith("//")
  )
    return "/channels";
  try {
    const url = new URL(value, "https://console.invalid");
    return url.origin === "https://console.invalid" &&
      url.pathname === "/channels"
      ? url.pathname + url.search + url.hash
      : "/channels";
  } catch {
    return "/channels";
  }
}
