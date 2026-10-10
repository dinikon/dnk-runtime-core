export interface StorageProvider {
  id: string;
  name: string;
  kind: string;
  is_system: boolean;
}
export interface StorageBucket {
  id: string;
  provider_id: string;
  name: string;
  status: "preparing" | "ready" | "purged";
  files_count: number;
  size_bytes: number;
}
export const bucketStatusLabels = {
  preparing: "Подготавливается",
  ready: "Готов",
  purged: "Удалён",
};
export function formatStorageBytes(bytes: number): string {
  if (bytes === 0) return "0 Б";
  const units = ["Б", "КиБ", "МиБ", "ГиБ", "ТиБ"];
  const index = Math.min(
    Math.floor(Math.log(bytes) / Math.log(1024)),
    units.length - 1,
  );
  return `${new Intl.NumberFormat("ru", { maximumFractionDigits: 1 }).format(bytes / 1024 ** index)} ${units[index]}`;
}
