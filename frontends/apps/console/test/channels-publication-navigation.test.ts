import test from "node:test";
import assert from "node:assert/strict";
import {
  publicationDetailsTab,
  publicationListQuery,
  publicationLinkQuery,
} from "../src/modules/channels/model/publication-navigation.ts";

test("publication tabs survive reload and binding links always reveal the binding editor", () => {
  assert.equal(publicationDetailsTab({}), "positions");
  assert.equal(
    publicationDetailsTab({ publication_tab: "bindings" }),
    "bindings",
  );
  assert.equal(
    publicationDetailsTab({ publication_tab: "unknown" }),
    "positions",
  );
  assert.equal(
    publicationDetailsTab({ binding: "new", publication_tab: "positions" }),
    "bindings",
  );
  assert.equal(
    publicationDetailsTab({ binding: ["wrong"], publication_tab: "positions" }),
    "positions",
  );
});
test("returning to the list keeps its filters without leaking publication editor state", () => {
  const query = {
    q: "shirt",
    locale: "uk",
    offset: "50",
    limit: "25",
    binding_filter: "unlinked",
    returnTo: "/channels?platform=prom",
    publication_tab: "bindings",
    binding: "group",
    binding_channel: "channel",
    binding_offset: "25",
    binding_limit: "50",
  };
  assert.deepEqual(publicationListQuery(query), {
    q: "shirt",
    locale: "uk",
    offset: "50",
    limit: "25",
    binding_filter: "unlinked",
    returnTo: "/channels?platform=prom",
  });
  assert.equal(query.binding, "group");
});
test("creating a binding from a publication uses the current channel and resets previous binding pagination", () => {
  assert.deepEqual(
    publicationLinkQuery(
      {
        locale: "ru",
        q: "SKU",
        binding: "old",
        binding_channel: "old-channel",
        binding_offset: "50",
      },
      "current",
    ),
    {
      locale: "ru",
      q: "SKU",
      publication_tab: "bindings",
      binding: "new",
      binding_channel: "current",
    },
  );
});
