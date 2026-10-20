import type { DraftValues } from "./catalog-links.types";
import { decimalLabel } from "./channels.presentation.ts";
export function editableDraft(values: DraftValues): DraftValues {
  return {
    ...values,
    titles: { ...values.titles },
    ...(values.descriptions
      ? { descriptions: { ...values.descriptions } }
      : {}),
    ...(values.gallery ? { gallery: [...values.gallery] } : {}),
    regularPrice:
      values.regularPrice === null ? null : decimalLabel(values.regularPrice),
    salePrice:
      values.salePrice === null ? null : decimalLabel(values.salePrice),
    quantity: values.quantity === null ? null : decimalLabel(values.quantity),
  };
}
export function confirmedDraft(
  values: DraftValues,
  includePrices: boolean,
): DraftValues {
  return {
    ...values,
    titles: Object.fromEntries(
      Object.entries(values.titles).map(([code, title]) => [
        code,
        title.trim(),
      ]),
    ),
    sku: values.sku?.trim() || null,
    regularPrice: includePrices
      ? values.regularPrice?.trim().replace(",", ".") || null
      : null,
    salePrice: includePrices
      ? values.salePrice?.trim().replace(",", ".") || null
      : null,
    currency: includePrices ? values.currency || null : null,
    quantity: values.manageStock
      ? values.quantity?.trim().replace(",", ".") || null
      : null,
    stockStatus: values.manageStock ? null : values.stockStatus,
    backorders: values.manageStock ? values.backorders : "no",
  };
}
export function draftFormIssue(values: DraftValues): string | null {
  if (
    Object.values(values.titles).some((title) => !title.trim()) ||
    Object.keys(values.titles).length < 1
  )
    return "Заполните названия для выбранных языков.";
  if (
    values.regularPrice !== null &&
    (!/^-?\d+(?:\.\d+)?$/.test(values.regularPrice) || !values.currency)
  )
    return "Укажите базовую цену и валюту либо отключите перенос цен.";
  if (values.salePrice !== null && !/^-?\d+(?:\.\d+)?$/.test(values.salePrice))
    return "Укажите корректную акционную цену.";
  if (
    values.manageStock &&
    (!values.quantity || !/^-?\d+$/.test(values.quantity))
  )
    return "Введите целое количество либо выберите ручное наличие.";
  if (!values.manageStock && !values.stockStatus)
    return "Выберите статус наличия.";
  return null;
}
