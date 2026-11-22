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
  metadata: (scope: FeedScope): readonly [...Root, "schema-metadata"] => [
    ...feedKeys.root(scope),
    "schema-metadata",
  ],
};
