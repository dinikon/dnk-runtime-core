import type { BindingPair, BindingPosition } from "./binding.types";
/** Только точные уникальные SKU, существующие пары имеют приоритет. */
export function suggestBindingPairs(
  catalog: readonly BindingPosition[],
  publications: readonly BindingPosition[],
  items: readonly BindingPair[],
  occupied: readonly string[],
): BindingPair[] {
  const left = new Map<string, BindingPosition[]>(),
    right = new Map<string, BindingPosition[]>();
  for (const p of catalog)
    if (p.sku) left.set(p.sku, [...(left.get(p.sku) ?? []), p]);
  for (const p of publications)
    if (p.sku && !occupied.includes(p.id))
      right.set(p.sku, [...(right.get(p.sku) ?? []), p]);
  const result = [...items];
  for (const [sku, positions] of left) {
    const targets = right.get(sku);
    if (
      positions.length === 1 &&
      targets?.length === 1 &&
      !result.some(
        (p) =>
          p.catalogId === positions[0]!.id ||
          p.publicationId === targets[0]!.id,
      )
    )
      result.push({
        catalogId: positions[0]!.id,
        publicationId: targets[0]!.id,
      });
  }
  return result;
}

import type { PublicationCard } from "../publication.types";
export function bindingPublicationPositions(
  card: PublicationCard,
): BindingPosition[] {
  return card.items.map((v) => ({
    id: v.id,
    kind: v.kind,
    title: v.title,
    sku: v.sku,
    imageUrl: v.mainImageUrl,
    status: v.status,
    price: v.price,
    currency: v.currency,
    quantity: v.quantity,
    availability: v.availability,
    stockSourceId: v.stockSourcePublicationId,
    externalId: v.externalId,
    stale: v.staleConfiguration,
  }));
}
