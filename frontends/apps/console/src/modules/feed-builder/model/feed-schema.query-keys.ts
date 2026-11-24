import { feedKeys, type FeedScope } from "./feed.query-keys.ts";
type Root = ReturnType<typeof feedKeys.root>;
export const feedSchemaKeys = {
  detail: (
    scope: FeedScope,
    id: string,
  ): readonly [...Root, "schema", string] => [
    ...feedKeys.root(scope),
    "schema",
    id,
  ],
  catalogCategories: (scope: FeedScope, locale: string | undefined): readonly [...Root, "catalog-category-tree", string | undefined] => [
    ...feedKeys.root(scope),
    "catalog-category-tree",
    locale,
  ],
  metadata: (scope: FeedScope): readonly [...Root, "schema-metadata"] => [
    ...feedKeys.root(scope),
    "schema-metadata",
  ],
};
