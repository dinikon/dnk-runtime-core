import type {
  Feed,
  FeedDraft,
  FeedSettings,
  FeedFieldErrors,
  FeedChanges,
} from "./feed.types.ts";
export function feedDraft(feed?: Feed): FeedDraft {
  const format = feed?.exportSettings.formatSettings;
  return {
    name: feed?.name ?? "",
    code: feed?.code ?? "",
    format: format?.format ?? "",
    delimiter: format?.format === "csv" ? format.delimiter : ",",
    includeHeader: format?.format === "csv" ? format.includeHeader : true,
    rootName: format?.format === "xml" ? format.rootName : "catalog",
    itemName: format?.format === "xml" ? format.itemName : "product",
  };
}
export function validateFeedDraft(draft: FeedDraft): FeedFieldErrors {
  const errors: FeedFieldErrors = {};
  const name = draft.name.trim(),
    code = draft.code.trim();
  if (!name || [...name].length > 255 || /\p{C}/u.test(name))
    errors.name = "Введите название до 255 символов без управляющих знаков.";
  if (!/^[a-z][a-z0-9_-]{0,63}$/.test(code))
    errors.code =
      "До 64 символов: латинские строчные буквы, цифры, _ и -. Начните с буквы.";
  if (!draft.format) errors.format = "Выберите CSV или XML.";
  if (
    draft.format === "csv" &&
    ([...draft.delimiter].length !== 1 ||
      draft.delimiter === '"' ||
      (draft.delimiter !== "\t" &&
        /[\p{C}\p{Zl}\p{Zp}]/u.test(draft.delimiter)))
  )
    errors.delimiter =
      "Один печатный символ или табуляция, кроме двойной кавычки.";
  if (draft.format === "xml")
    for (const field of ["rootName", "itemName"] as const) {
      if (!/^[A-Za-z_][A-Za-z0-9_.-]{0,127}$/.test(draft[field]))
        errors[field] =
          "До 128 символов: латинские буквы, цифры, _, . и -. Начните с буквы или _.";
    }
  return errors;
}
export function draftSettings(draft: FeedDraft): FeedSettings {
  if (Object.keys(validateFeedDraft(draft)).length)
    throw new Error("Invalid feed draft");
  return {
    name: draft.name.trim(),
    code: draft.code.trim(),
    exportSettings: {
      formatSettings:
        draft.format === "csv"
          ? {
              format: "csv",
              delimiter: draft.delimiter,
              includeHeader: draft.includeHeader,
              encoding: "utf-8",
            }
          : {
              format: "xml",
              rootName: draft.rootName,
              itemName: draft.itemName,
              encoding: "utf-8",
            },
      productMode: "VARIABLE_TO_SINGLE",
      validationPolicy: "STRICT",
    },
  };
}
export function feedChanges(
  base: FeedSettings,
  next: FeedSettings,
): FeedChanges {
  return {
    ...(base.name !== next.name ? { name: next.name } : {}),
    ...(base.code !== next.code ? { code: next.code } : {}),
    ...(JSON.stringify(base.exportSettings) !==
    JSON.stringify(next.exportSettings)
      ? { exportSettings: next.exportSettings }
      : {}),
  };
}
/** Only the submitted snapshot is acknowledged; later input remains dirty. */
export function acknowledgeFeedDraft(
  current: FeedDraft,
  sent: FeedDraft,
  saved: Feed,
): FeedDraft {
  return JSON.stringify(current) === JSON.stringify(sent)
    ? feedDraft(saved)
    : { ...current };
}
