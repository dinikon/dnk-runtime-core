/** Schema values contain JSON primitives only; this also accepts Vue proxy inputs. */
export function cloneSchemaValue<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}
