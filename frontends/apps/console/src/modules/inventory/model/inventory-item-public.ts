/** Контекст успешного PATCH для внешней сборки зависимых модулей. */
export function inventoryItemUpdateTenant(
  key: readonly unknown[] | undefined,
  variables: unknown,
): string | null {
  if (
    !key ||
    key.length !== 7 ||
    typeof key[2] !== "string" ||
    typeof key[3] !== "string" ||
    typeof key[6] !== "string" ||
    key[0] !== "inventory" ||
    key[4] !== "items" ||
    key[5] !== "update" ||
    typeof key[1] !== "string" ||
    typeof variables !== "object" ||
    variables === null ||
    !("signal" in variables) ||
    !(variables.signal instanceof AbortSignal) ||
    variables.signal.aborted ||
    !("id" in variables) ||
    variables.id !== key[6] ||
    !("scope" in variables) ||
    !Array.isArray(variables.scope) ||
    variables.scope.length !== 3 ||
    !variables.scope.every((part, index) => part === key[index + 1])
  )
    return null;
  return key[1];
}
