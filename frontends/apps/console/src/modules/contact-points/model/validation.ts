import { parsePhoneNumberFromString } from "libphonenumber-js/max";
import type {
  ContactPointDraft,
  ContactPointKind,
  ContactPointErrors,
  ContactPointArrays,
  ContactPointDto,
} from "./types";

export function mapContactPoint(dto: ContactPointDto): ContactPointDraft {
  return {
    clientKey: dto.binding_id,
    bindingId: dto.binding_id,
    contactPointId: dto.contact_point_id,
    value: dto.value,
    labelId: dto.label_id,
    countryCode: dto.country_code ?? undefined,
  };
}

export function contactPointPayload(
  rows: ContactPointDraft[],
  kind: ContactPointKind,
) {
  return rows.map((row) => ({
    value: row.value.trim(),
    binding_id: row.bindingId ?? null,
    label_id: row.labelId,
    ...(kind === "phone" ? { country_code: row.countryCode } : {}),
  }));
}

export function validateContactPoints(
  rows: ContactPointDraft[],
  kind: ContactPointKind,
): ContactPointErrors {
  const errors: ContactPointErrors = {};
  const seen = new Set<string>();
  for (const row of rows) {
    const value = row.value.trim();
    let canonical = value;
    if (kind === "phone") {
      const phone = parsePhoneNumberFromString(value, {
        defaultCountry: row.countryCode,
        extract: false,
      });
      if (!row.countryCode)
        errors[row.clientKey] = { countryCode: "Выберите страну." };
      else if (
        !phone?.isValid() ||
        phone.country !== row.countryCode ||
        phone.ext
      ) {
        errors[row.clientKey] = {
          value:
            "Введите корректный номер выбранной страны без добавочного номера.",
        };
      } else canonical = phone.number;
    } else {
      const at = value.lastIndexOf("@");
      if (!/^[^\s@]+@[^\s@.]+(?:\.[^\s@.]+)+$/u.test(value)) {
        errors[row.clientKey] = {
          value: "Введите email в формате name@domain.com.",
        };
      } else
        canonical =
          value.slice(0, at) + "@" + value.slice(at + 1).toLowerCase();
    }
    if (!errors[row.clientKey] && seen.has(canonical))
      errors[row.clientKey] = { value: "Это значение уже добавлено." };
    seen.add(canonical);
  }
  return errors;
}

export function contactPointServerErrors(
  cause: unknown,
  snapshot: ContactPointArrays,
): ContactPointErrors {
  const detail = (cause as { response?: { data?: { detail?: unknown } } })
    ?.response?.data?.detail;
  if (!Array.isArray(detail)) return {};
  const fields: Record<
    string,
    "value" | "labelId" | "countryCode" | "bindingId"
  > = {
    value: "value",
    label_id: "labelId",
    country_code: "countryCode",
    binding_id: "bindingId",
  };
  const errors: ContactPointErrors = {};
  for (const error of detail) {
    if (!Array.isArray(error.loc)) continue;
    const [, array, index, field] = error.loc as unknown[];
    if (array !== "phones" && array !== "emails") continue;
    const row = snapshot[array][Number(index)];
    if (row)
      errors[row.clientKey] = {
        ...errors[row.clientKey],
        [fields[String(field)] ?? "value"]: String(error.msg),
      };
  }
  return errors;
}
