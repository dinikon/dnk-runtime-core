import type {
  PublicationReference,
  PublicationChoice,
} from "./feed-publication.types.ts";
export const MAX_PUBLICATION_SELECTION = 100;
export function publicationReferenceKey(value: PublicationReference): string {
  return JSON.stringify([value.itemId, value.variantId]);
}
export function mergePublicationChoices(
  current: PublicationChoice[],
  added: PublicationChoice[],
): PublicationChoice[] {
  const values = new Map(current.map((v) => [publicationReferenceKey(v), v]));
  for (const v of added) values.set(publicationReferenceKey(v), v);
  if (values.size > MAX_PUBLICATION_SELECTION)
    throw new Error("Выберите не более 100 позиций за одно добавление.");
  return [...values.values()];
}
export function togglePublicationChoice(
  current: PublicationChoice[],
  choice: PublicationChoice,
): PublicationChoice[] {
  const key = publicationReferenceKey(choice);
  return current.some((v) => publicationReferenceKey(v) === key)
    ? current.filter((v) => publicationReferenceKey(v) !== key)
    : mergePublicationChoices(current, [choice]);
}
