import type { FeedScope } from "./feed.query-keys.ts";
type CalculationRootKey = readonly ["feed-builder", ...FeedScope];
type CalculationMetadataKey = readonly [
  ...CalculationRootKey,
  "calculation-metadata",
];
type CalculationProductsKey = readonly [
  ...CalculationRootKey,
  "preview-products",
  string,
  string,
  number,
];
type CalculationVariantsKey = readonly [
  ...CalculationRootKey,
  "preview-variants",
  string | undefined,
  string,
  number,
];
export const calculationKeys = {
  metadata: (scope: FeedScope): CalculationMetadataKey =>
    ["feed-builder", ...scope, "calculation-metadata"] as const,
  products: (
    scope: FeedScope,
    locale: string,
    search: string,
    offset: number,
  ): CalculationProductsKey =>
    [
      "feed-builder",
      ...scope,
      "preview-products",
      locale,
      search,
      offset,
    ] as const,
  variants: (
    scope: FeedScope,
    rootId: string | undefined,
    locale: string,
    offset: number,
  ): CalculationVariantsKey =>
    [
      "feed-builder",
      ...scope,
      "preview-variants",
      rootId,
      locale,
      offset,
    ] as const,
};
