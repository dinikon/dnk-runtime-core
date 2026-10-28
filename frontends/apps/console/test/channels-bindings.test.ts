import { test } from "node:test";
import assert from "node:assert/strict";
import { suggestBindingPairs } from "../src/modules/channels/model/bindings/binding.matching.ts";
import {
  bindingPosition,
  bindingPreview,
  bindingProposal,
} from "../src/modules/channels/api/binding.mapper.ts";
import { parsePublicationFilters } from "../src/modules/channels/model/publication.filters.ts";
import type { BindingPosition } from "../src/modules/channels/model/bindings/binding.types.ts";
function position(id: string, sku: string | null): BindingPosition {
  return {
    id,
    sku,
    kind: "variant",
    title: null,
    imageUrl: null,
    status: "archived",
    price: "123456789012345.000001",
    currency: "USD",
    quantity: null,
    availability: null,
    stockSourceId: id,
    externalId: null,
    stale: false,
  };
}
test("Suggestions need exact unique SKUs, preserve explicit pairs and exclude claims", () => {
  const catalog = [
    position("s", "S"),
    position("m", "M"),
    position("l", "D"),
    position("xl", "D"),
    position("none", null),
  ];
  const pubs = [
    position("one", "S"),
    position("two", "M"),
    position("three", "D"),
    position("four", null),
  ];
  assert.deepEqual(suggestBindingPairs(catalog, pubs, [], ["two"]), [
    { catalogId: "s", publicationId: "one" },
  ]);
  assert.deepEqual(
    suggestBindingPairs(
      catalog,
      pubs,
      [{ catalogId: "s", publicationId: "two" }],
      [],
    ),
    [{ catalogId: "s", publicationId: "two" }],
  );
  assert.deepEqual(
    suggestBindingPairs([position("a", " X ")], [position("b", "X")], [], []),
    [],
  );
  assert.deepEqual(
    suggestBindingPairs(
      [position("a", "x")],
      [position("b", "x"), position("c", "x")],
      [],
      [],
    ),
    [],
  );
});
test("Binding mapping keeps decimals, unknown values, source ownership and structural tokens", () => {
  const dto = {
    id: "s",
    kind: "variant",
    title: null,
    sku: "S",
    image_url: null,
    status: "archived",
    price: "123456789012345.000001",
    currency: "USD",
    quantity: null,
    availability: null,
    stock_source_id: "parent",
    external_id: "202",
    stale: true,
  };
  const result = bindingPosition(dto);
  assert.equal(result.price, dto.price);
  assert.equal(result.title, null);
  assert.equal(result.stockSourceId, "parent");
  assert.equal(result.stale, true);
  const preview = bindingPreview({
    catalog: null,
    publications: [dto],
    assessment: {
      state: "conflict",
      issues: ["binding_catalog_missing"],
      catalog_count: 0,
      publication_count: 1,
      matched_count: 1,
    },
    catalog_token: "left",
    publication_token: "right",
    suggestions: [],
  });
  assert.equal(preview.state, "conflict");
  assert.equal(preview.catalogRoot, null);
  assert.equal(preview.publicationToken, "right");
});
test("Proposal serializes immutable scope, explicit pairs and optional existing group", () => {
  const proposal = {
    catalogRootId: "root",
    mode: "VARIABLE_TO_SIMPLE" as const,
    publicationRootId: null,
    items: [{ catalogId: "s", publicationId: "one" }],
    locale: "uk",
    groupId: "group",
  };
  const dto = bindingProposal(proposal);
  assert.deepEqual(dto, {
    catalog_root_id: "root",
    mode: "VARIABLE_TO_SIMPLE",
    publication_root_id: null,
    items: [{ catalog_position_id: "s", publication_id: "one" }],
    locale: "uk",
    group_id: "group",
  });
  dto.items[0]!.publication_id = "changed";
  assert.equal(proposal.items[0]!.publicationId, "one");
});
test("Linked filter survives URL and ignores unsupported values without dropping paging", () => {
  assert.deepEqual(
    parsePublicationFilters({
      binding_filter: "linked",
      limit: "50",
      offset: "50",
      q: "S",
      locale: "ru",
    }),
    { binding: "linked", limit: 50, offset: 50, search: "S", locale: "ru" },
  );
  assert.equal(
    parsePublicationFilters({ binding_filter: "invented" }).binding,
    undefined,
  );
});

// A network/server failure may happen after commit; a validation failure is definite.
test("Only ambiguous create failures require checking the refreshed group list", async () => {
  const { bindingCreationUncertain } =
    await import("../src/modules/channels/model/bindings/binding.errors.ts");
  assert.equal(bindingCreationUncertain({ isAxiosError: true }), true);
  assert.equal(
    bindingCreationUncertain({ isAxiosError: true, response: { status: 503 } }),
    true,
  );
  assert.equal(
    bindingCreationUncertain({ isAxiosError: true, response: { status: 422 } }),
    false,
  );
  assert.equal(
    bindingCreationUncertain({ isAxiosError: true, response: { status: 409 } }),
    false,
  );
});
