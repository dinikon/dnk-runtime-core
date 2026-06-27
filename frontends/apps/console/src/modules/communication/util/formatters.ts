import type { JsonObject } from "@/modules/communication/api";

export function formatCommunicationDate(value: string | null | undefined) {
  if (!value) {
    return "-";
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function isArchivedStatus(status: string) {
  return status.startsWith("ARCHIV");
}

export function prettyJson(value: JsonObject) {
  return JSON.stringify(value, null, 2);
}

export function shortCommunicationId(value: string) {
  return value.slice(0, 8);
}
