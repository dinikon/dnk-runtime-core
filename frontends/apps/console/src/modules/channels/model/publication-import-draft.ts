import { z } from "zod";
import type { ImportDraftValues } from "./publication-import.types";
import type { CreateDraftInput } from "./catalog-links.types";
const valuesSchema = z
  .object({
    copyPrices: z.boolean().optional(),
    titles: z.record(z.string(), z.string().max(2000)),
    descriptions: z.record(z.string(), z.string().max(300000)),
    gallery: z.array(z.string().max(200)).max(100),
    primaryImageId: z.string().nullable(),
    sku: z.string().nullable(),
    regularPrice: z.string().nullable(),
    salePrice: z.string().nullable(),
    currency: z.string().nullable(),
    manageStock: z.boolean(),
    quantity: z.string().nullable(),
    stockStatus: z.string().nullable(),
    backorders: z.string(),
  })
  .strict();
const inputSchema = z
  .object({
    publicationId: z.string(),
    preparationId: z.string(),
    preparationRevision: z.number().int(),
    requestKey: z.string(),
    observedRevision: z.number().int(),
    values: valuesSchema,
  })
  .strict();
const recordSchema = z
  .object({
    version: z.literal(1),
    expiresAt: z.string(),
    baseline: z.string(),
    values: valuesSchema,
    intent: inputSchema.nullable(),
    uncertain: z.boolean(),
  })
  .strict();
export interface PublicationImportDraftRecord {
  version: 1;
  expiresAt: string;
  baseline: string;
  values: ImportDraftValues;
  intent: CreateDraftInput | null;
  uncertain: boolean;
}
export function restorePublicationImportDraft(
  raw: string | null,
  now: number = Date.now(),
): PublicationImportDraftRecord | null {
  if (!raw || raw.length > 1500000) return null;
  try {
    const parsed = recordSchema.safeParse(JSON.parse(raw));
    if (!parsed.success) return null;
    const expiry = Date.parse(parsed.data.expiresAt);
    if (
      !Number.isFinite(expiry) ||
      now >= expiry + (parsed.data.uncertain ? 7 * 86400000 : 0)
    )
      return null;
    return parsed.data;
  } catch {
    return null;
  }
}
export function copyImportValues(values: ImportDraftValues): ImportDraftValues {
  return {
    ...values,
    titles: { ...values.titles },
    descriptions: { ...values.descriptions },
    gallery: [...values.gallery],
  };
}
export function moveImportImage(
  values: ImportDraftValues,
  id: string,
  offset: number,
): ImportDraftValues {
  const next = copyImportValues(values),
    index = next.gallery.indexOf(id),
    target = index + offset;
  if (index >= 0 && target >= 0 && target < next.gallery.length)
    [next.gallery[index], next.gallery[target]] = [
      next.gallery[target]!,
      next.gallery[index]!,
    ];
  return next;
}
export function removeImportImage(
  values: ImportDraftValues,
  id: string,
): ImportDraftValues {
  const next = copyImportValues(values);
  next.gallery = next.gallery.filter((key) => key !== id);
  if (next.primaryImageId === id) next.primaryImageId = next.gallery[0] ?? null;
  return next;
}
