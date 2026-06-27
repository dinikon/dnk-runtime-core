export function createClientUuid() {
  if (globalThis.crypto?.randomUUID) {
    return globalThis.crypto.randomUUID();
  }

  return "10000000-1000-4000-8000-100000000000".replace(/[018]/g, (value) =>
    (
      Number(value) ^
      (globalThis.crypto.getRandomValues(new Uint8Array(1))[0] &
        (15 >> (Number(value) / 4)))
    ).toString(16),
  );
}
