import type { PublicationCard } from "./publication.types";

function imageUrl(value: string | null | undefined): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    return ["http:", "https:"].includes(url.protocol) &&
      !url.username &&
      !url.password
      ? url.href
      : null;
  } catch {
    return null;
  }
}

export function publicationThumbnail(card: PublicationCard): string | null {
  if (card.rootKind === "variable") return imageUrl(card.rootMainImageUrl);
  const selected = card.items.find(
    (item) => item.id === card.selectedPublicationId,
  );
  const selectedUrl = imageUrl(selected?.mainImageUrl);
  if (selectedUrl) return selectedUrl;
  for (const item of card.items) {
    const url = imageUrl(item.mainImageUrl);
    if (url) return url;
  }
  return null;
}
