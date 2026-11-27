import { newCategoryType } from "./feed-categories.draft.ts";
import { calculationIsSupported, categoryMembershipIssuePath } from "./feed-calculation.draft.ts";
import { cloneSchemaValue } from "./feed-schema.clone.ts";
import type {
  FieldKind,
  SchemaField,
  SchemaFieldDraft,
  FeedSchemaDraft,
  FeedSchemaDefinition,
  SchemaMetadata,
  SchemaIssue,
  SchemaTransform,
  DraftTransform,
} from "./feed-schema.types.ts";
function draftTransform(t: SchemaTransform): DraftTransform {
  return {
    operation: t.operation,
    parameter:
      t.operation === "string.truncate"
        ? String(t.parameters.maxLength)
        : t.operation === "money.ceil_step"
          ? t.parameters.step
          : "",
  };
}
export function fieldDraft(field: SchemaField): SchemaFieldDraft {
  const clone = cloneSchemaValue(field),
    type = clone.typeDefinition;
  if (type.kind === "boolean" || type.kind === "category") return { ...clone, typeDefinition: type };
  if (type.kind === "integer") return {
    ...clone,
    typeDefinition: {
      ...type,
      value: type.value.kind === "CONSTANT"
        ? { kind: "CONSTANT", value: String(type.value.value) } : type.value,
      constraints: {
        required: type.constraints.required,
        minValue: type.constraints.minValue === null ? "" : String(type.constraints.minValue),
        maxValue: type.constraints.maxValue === null ? "" : String(type.constraints.maxValue),
      },
    },
  };
  return {
    ...clone,
    typeDefinition:
      type.kind === "money"
        ? {
            ...type,
            constraints: {
              required: type.constraints.required,
              minAmount: type.constraints.minAmount ?? "",
              maxAmount: type.constraints.maxAmount ?? "",
            },
            transforms: type.transforms.map(draftTransform),
          }
        : {
            ...type,
            constraints: {
              required: type.constraints.required,
              minLength:
                type.constraints.minLength === null
                  ? ""
                  : String(type.constraints.minLength),
              maxLength:
                type.constraints.maxLength === null
                  ? ""
                  : String(type.constraints.maxLength),
            },
            transforms: type.transforms.map(draftTransform),
          },
  };
}
export function schemaDraft(schema: FeedSchemaDefinition): FeedSchemaDraft {
  return { fields: schema.fields.map(fieldDraft), ...(schema.categoryTrees ? { categoryTrees: cloneSchemaValue(schema.categoryTrees) } : {}) };
}
export function newSchemaField(
  kind: FieldKind,
  id: string,
  used: SchemaFieldDraft[],
  locale = "uk",
): SchemaFieldDraft {
  let n = 1;
  while (
    used.some((f) => f.key === `field_${n}` || f.export.name === `field_${n}`)
  )
    n++;
  const common = {
    id,
    key: `field_${n}`,
    label: "Новое поле",
    export: { name: `field_${n}`, enabled: true, xmlPlacement: "ELEMENT" as const },
    aiInstruction: null,
  };
  if (kind === "category") return {
    ...common,
    export: { ...common.export, publication: { valueKey: "id", required: false } },
    typeDefinition: newCategoryType(locale),
  };
  if (kind === "integer") return {
    ...common,
    typeDefinition: {
      kind, value: { kind: "SOURCE", source: { provider: "catalog", path: "item.stock_quantity" } },
      constraints: { required: false, minValue: "", maxValue: "" },
    },
  };
  if (kind === "boolean") return {
    ...common,
    typeDefinition: {
      kind, value: { kind: "SOURCE", source: { provider: "catalog", path: "item.in_stock" } },
      constraints: { required: false },
    },
  };
  return {
    ...common,
    typeDefinition:
      kind === "money"
        ? {
            kind,
            currency: null,
            value: {
              kind: "MONEY",
              mode: "SOURCE",
              source: { provider: "catalog", path: "item.regular_price" },
            },
            constraints: { required: false, minAmount: "", maxAmount: "" },
            transforms: [],
          }
        : {
            kind,
            locale: kind === "rich_text" ? locale : null,
            fallbackPolicy: null,
            value: {
              kind: "SOURCE",
              source: { provider: "catalog", path: kind === "rich_text" ? "item.description_html" : "" },
            },
            constraints: { required: false, minLength: "", maxLength: "" },
            transforms: [],
          },
  };
}
export function duplicateSchemaField(
  field: SchemaFieldDraft,
  id: string,
  fields: SchemaFieldDraft[],
): SchemaFieldDraft {
  const clone = cloneSchemaValue(field);
  let n = 1;
  const key = field.key.slice(0, 52),
    name = field.export.name.slice(0, 116);
  while (
    fields.some(
      (f) =>
        f.key === `${key}_copy_${n}` || f.export.name === `${name}_copy_${n}`,
    )
  )
    n++;
  return {
    ...clone,
    id,
    ...(clone.categoryTreeId ? { categoryTreeId: id } : {}),
    key: `${key}_copy_${n}`,
    label: `${field.label.slice(0, 247)} (копия)`,
    export: {
      ...clone.export, name: `${name}_copy_${n}`,
      ...(clone.export.document ? { document: {
        ...clone.export.document,
        container: `${clone.export.document.container.slice(0, 115)}_copy_${n}`,
      } } : {}),
    },
  };
}
export function moveSchemaField(
  fields: SchemaFieldDraft[],
  id: string,
  delta: number,
): SchemaFieldDraft[] {
  const index = fields.findIndex((f) => f.id === id),
    target = index + delta;
  if (index < 0 || target < 0 || target >= fields.length) return fields;
  const result = [...fields];
  const [item] = result.splice(index, 1);
  result.splice(target, 0, item!);
  return result;
}
export function fieldCanPreview(field?: SchemaFieldDraft | null): boolean {
  const type = field?.typeDefinition;
  if (!type) return false;
  if (type.kind === "money") return type.value.mode !== "MANUAL";
  return (type.kind === "integer" || type.kind === "boolean") && type.value.kind !== "MANUAL";
}

export function parseFeedInteger(value: string): number | undefined {
  const text = value.trim();
  if (!/^[+-]?[0-9]+$/.test(text)) return;
  const parsed = Number(text);
  return Number.isSafeInteger(parsed) ? parsed : undefined;
}

export function fieldIsReadonly(field: SchemaFieldDraft): boolean {
  return (
    field.typeDefinition.kind === "money" &&
    field.typeDefinition.value.mode === "CALCULATED" &&
    !calculationIsSupported(field.typeDefinition.value.calculation)
  );
}
function decimalParts(
  text: string,
): { coefficient: bigint; exponent: number } | undefined {
  const match =
    /^([+-]?)(?:(\d+)(?:\.(\d*))?|\.(\d+))(?:[eE]([+-]?\d+))?$/.exec(
      text.trim(),
    );
  if (!match || text.length > 256) return;
  const fraction = match[3] ?? match[4] ?? "",
    digits = ((match[2] ?? "") + fraction).replace(/^0+/, "") || "0";
  const exponent = Number(match[5] ?? 0) - fraction.length;
  if (
    digits.length > 40 ||
    !Number.isSafeInteger(exponent) ||
    Math.abs(exponent) > 128
  )
    return;
  return {
    coefficient: BigInt(`${match[1] === "-" ? "-" : ""}${digits}`),
    exponent,
  };
}
function compareDecimals(a: string, b: string): number | undefined {
  const first = decimalParts(a),
    second = decimalParts(b);
  if (!first || !second) return;
  const exp = Math.min(first.exponent, second.exponent);
  const left = first.coefficient * 10n ** BigInt(first.exponent - exp),
    right = second.coefficient * 10n ** BigInt(second.exponent - exp);
  return left < right ? -1 : left > right ? 1 : 0;
}
export function validateSchemaDraft(
  draft: FeedSchemaDraft,
  metadata: SchemaMetadata,
): SchemaIssue[] {
  const errors: SchemaIssue[] = [],
    keys = new Set<string>(),
    ids = new Set<string>(),
    names = new Set<string>();
  if (draft.fields.length > metadata.maxFields)
    errors.push({
      code: "SCHEMA_LIMIT",
      message: `Допустимо не более ${metadata.maxFields} полей.`,
      path: [],
    });
  draft.fields.forEach((field, index) => {
    const path = ["definition", "fields", index];
    const error = (suffix: (string | number)[], message: string): void => {
      errors.push({
        code: "SCHEMA_INVALID",
        message,
        fieldId: field.id,
        path: [...path, ...suffix],
      });
    };
    if (!/^[0-9a-f-]{36}$/i.test(field.id) || ids.has(field.id))
      error(["id"], "Идентификатор поля должен быть уникальным UUID.");
    if (
      !/^[A-Za-z_][A-Za-z0-9_]{0,63}$/.test(field.key.trim()) ||
      keys.has(field.key.trim())
    )
      error(
        ["key"],
        "Уникальный ключ до 64 символов: латинские буквы, цифры и _. Начните с буквы или _.",
      );
    if (
      !field.label.trim() ||
      [...field.label.trim()].length > 255 ||
      /\p{C}/u.test(field.label)
    )
      error(
        ["label"],
        "Введите подпись до 255 символов без управляющих знаков.",
      );
    if (
      !/^[A-Za-z_][A-Za-z0-9_.-]{0,127}$/.test(field.export.name.trim()) ||
      ((field.typeDefinition.kind !== "category" || field.export.publication) && names.has(field.export.name.trim()))
    )
      error(
        ["export", "name"],
        "Нужно уникальное имя колонки или XML-тега до 128 символов.",
      );
    if (field.export.xmlPlacement === "ATTRIBUTE" && field.export.name.trim() === "xmlns")
      error(["export", "name"], "Имя xmlns зарезервировано для пространства имён XML.");
    ids.add(field.id);
    keys.add(field.key.trim());
    if (field.typeDefinition.kind !== "category" || field.export.publication) names.add(field.export.name.trim());
    const type = field.typeDefinition;
    if (type.kind === "category") {
      if (field.export.enabled && !field.export.document && !field.export.publication)
        error(["export"], "Выберите вывод дерева или ссылки.");
      if (field.export.publication && !type.objectSchema.fields.some((prop) => prop.key === field.export.publication?.valueKey))
        error(["export", "publication"], "Выберите свойство для ссылки.");
      type.value.rules.forEach((rule, index) => {
        const issue = categoryMembershipIssuePath(rule.condition, ["value", "rules", index, "condition"]);
        if (issue)
          error(issue, `В правиле «${rule.label}» укажите справа UUID категории Catalog.`);
      });
      return;
    }
    const source =
      type.kind === "money"
        ? type.value.mode === "SOURCE"
          ? type.value.source
          : undefined
        : type.value.kind === "SOURCE"
          ? type.value.source
          : undefined;
    if (source) {
      const entry = metadata.sources.find(
        (s) =>
          s.path === source.path &&
          s.provider === source.provider &&
          s.fieldKinds.includes(type.kind),
      );
      if (!entry)
        error(
          ["data", "value", "source"],
          "Выберите совместимый источник.",
        );
      else if (type.kind === "string" || type.kind === "text" || type.kind === "rich_text") {
        if (entry.requiresLocale && !type.locale)
          error(["data", "locale"], "Выберите локаль источника.");
        if (!entry.requiresLocale && (type.locale || type.fallbackPolicy))
          error(
            ["data", "locale"],
            "Этот источник не использует локаль или fallback.",
          );
      }
    }
    if (type.kind === "boolean") return;
    if (type.kind === "integer") {
      const { minValue, maxValue } = type.constraints;
      const minimum = parseFeedInteger(minValue);
      const maximum = parseFeedInteger(maxValue);
      if (
        (minValue.trim() && minimum === undefined) ||
        (maxValue.trim() && maximum === undefined) ||
        (minimum !== undefined && maximum !== undefined && minimum > maximum)
      ) error(["data", "constraints"], "Укажите целые границы от меньшей к большей.");
      if (type.value.kind === "CONSTANT") {
        const value = parseFeedInteger(type.value.value);
        if (value === undefined || (minimum !== undefined && value < minimum) ||
            (maximum !== undefined && value > maximum))
          error(["data", "value"], "Укажите целое число в границах поля.");
      }
      return;
    }
    if (type.kind !== "money") {
      const available = new Set(metadata.locales.map((l) => l.code));
      if (type.locale && !available.has(type.locale))
        error(
          ["data", "locale"],
          "Локаль недоступна в справочнике.",
        );
      if (type.fallbackPolicy) {
        if (
          !type.locale ||
          type.fallbackPolicy.locales.some(
            (l) => !available.has(l) || l === type.locale,
          ) ||
          new Set(type.fallbackPolicy.locales).size !==
            type.fallbackPolicy.locales.length ||
          (type.fallbackPolicy.mode === "LOCALE_CHAIN" &&
            !type.fallbackPolicy.locales.length)
        )
          error(
            ["data", "fallback_policy"],
            "Укажите непустую цепочку доступных локалей без повторов и основной локали.",
          );
      }
      for (const key of ["minLength", "maxLength"] as const)
        if (
          type.constraints[key] &&
          (!/^\d+$/.test(type.constraints[key]) ||
            !Number.isSafeInteger(Number(type.constraints[key])))
        )
          error(
            ["data", "constraints"],
            "Длина должна быть неотрицательным целым числом.",
          );
      if (
        type.constraints.minLength &&
        type.constraints.maxLength &&
        Number(type.constraints.minLength) > Number(type.constraints.maxLength)
      )
        error(
          ["data", "constraints"],
          "Минимальная длина превышает максимальную.",
        );
    } else {
      if (type.currency && !/^[A-Za-z]{3}$/.test(type.currency.trim()))
        error(
          ["data", "currency"],
          "Укажите трёхбуквенный код валюты или оставьте поле пустым.",
        );
      for (const key of ["minAmount", "maxAmount"] as const)
        if (type.constraints[key] && !decimalParts(type.constraints[key]))
          error(
            ["data", "constraints"],
            "Сумма должна быть конечным числом с точкой без потери точности.",
          );
      if (
        type.constraints.minAmount &&
        type.constraints.maxAmount &&
        compareDecimals(
          type.constraints.minAmount,
          type.constraints.maxAmount,
        ) === 1
      )
        error(
          ["data", "constraints"],
          "Минимальная сумма превышает максимальную.",
        );
    }
    if (type.transforms.length > metadata.maxTransforms)
      error(
        ["data", "transforms"],
        "Превышен лимит преобразований.",
      );
    type.transforms.forEach((t) => {
      if (
        !metadata.transforms.some(
          (m) =>
            m.operation === t.operation && m.fieldKinds.includes(type.kind),
        )
      )
        error(
          ["data", "transforms"],
          "Преобразование несовместимо с типом.",
        );
      if (
        t.operation === "string.truncate" &&
        (!/^\d+$/.test(t.parameter) ||
          !Number.isSafeInteger(Number(t.parameter)))
      )
        error(
          ["data", "transforms"],
          "Длина обрезания должна быть неотрицательным целым числом.",
        );
      if (
        t.operation === "money.ceil_step" &&
        (compareDecimals(t.parameter, "0") ?? 0) <= 0
      )
        error(
          ["data", "transforms"],
          "Шаг округления должен быть положительным числом.",
        );
    });
  });
  return errors;
}
function transformValue(t: DraftTransform): SchemaTransform {
  return t.operation === "string.truncate"
    ? { operation: t.operation, parameters: { maxLength: Number(t.parameter) } }
    : t.operation === "money.ceil_step"
      ? { operation: t.operation, parameters: { step: t.parameter.trim() } }
      : { operation: t.operation, parameters: {} };
}
export function draftDefinition(
  draft: FeedSchemaDraft,
  metadata: SchemaMetadata,
): FeedSchemaDefinition {
  if (validateSchemaDraft(draft, metadata).length)
    throw new Error("Invalid schema draft");
  return {
    schemaFormatVersion: 2,
    ...(draft.categoryTrees ? { categoryTrees: cloneSchemaValue(draft.categoryTrees) } : {}),
    fields: draft.fields.map((f) => {
      const field = cloneSchemaValue(f),
        type = field.typeDefinition;
      const common = {
        ...field,
        key: field.key.trim(),
        label: field.label.trim(),
        export: { ...field.export, name: field.export.name.trim() },
      };
      if (type.kind === "boolean" || type.kind === "category") return { ...common, typeDefinition: type };
      if (type.kind === "integer") {
        return { ...common, typeDefinition: {
          ...type,
          value: type.value.kind === "CONSTANT"
            ? { kind: "CONSTANT", value: parseFeedInteger(type.value.value)! } : type.value,
          constraints: {
            required: type.constraints.required,
            minValue: parseFeedInteger(type.constraints.minValue) ?? null,
            maxValue: parseFeedInteger(type.constraints.maxValue) ?? null,
          },
        } };
      }
      return {
        ...common,
        typeDefinition:
          type.kind === "money"
            ? {
                ...type,
                currency: type.currency?.trim().toUpperCase() || null,
                value: type.value as import("./feed-schema.types").MoneyValue,
                constraints: {
                  required: type.constraints.required,
                  minAmount: type.constraints.minAmount.trim() || null,
                  maxAmount: type.constraints.maxAmount.trim() || null,
                },
                transforms: type.transforms.map(transformValue),
              }
            : {
                ...type,
                value: type.value as import("./feed-schema.types").TextValue,
                constraints: {
                  required: type.constraints.required,
                  minLength: type.constraints.minLength
                    ? Number(type.constraints.minLength)
                    : null,
                  maxLength: type.constraints.maxLength
                    ? Number(type.constraints.maxLength)
                    : null,
                },
                transforms: type.transforms.map(transformValue),
              },
      };
    }),
  };
}
export function acknowledgeSchemaDraft(
  current: FeedSchemaDraft,
  sent: FeedSchemaDraft,
  saved: FeedSchemaDefinition,
): FeedSchemaDraft {
  return JSON.stringify(current) === JSON.stringify(sent)
    ? schemaDraft(saved)
    : current;
}
