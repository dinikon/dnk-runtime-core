import { test } from "node:test";
import assert from "node:assert/strict";
import { effectScope, nextTick, ref } from "vue";
import { useProductContentDraft } from "../src/modules/catalog/model/use-product-content-draft.ts";

test("refetch cannot replace newer unsaved content; clean content accepts server values", async () => {
  const scope = effectScope();
  const source = ref<Record<string, string> | null>({
    title: "Server",
    body: "Full",
  });
  const dirty = ref(false);
  const saved: Record<string, string>[] = [];
  const draft = scope.run(() =>
    useProductContentDraft(
      () => source.value,
      () => "tenant:item:ru",
      () => dirty.value,
      (value) => {
        saved.push(value);
        dirty.value = true;
      },
    ),
  )!;
  draft.change("title", "Newer");
  source.value = { title: "Older acknowledgement", body: "Full" };
  await nextTick();
  assert.equal(draft.values.value.title, "Newer");
  draft.change("body", "Updated body");
  assert.deepEqual(saved.at(-1), {
    title: "Newer",
    body: "Updated body",
  });
  dirty.value = false;
  source.value = { title: "Canonical", body: "Clean" };
  await nextTick();
  assert.deepEqual(draft.values.value, source.value);
  scope.stop();
});

test("scope switch and explicit reload reset content without staging a write", async () => {
  const effects = effectScope();
  const source = ref<Record<string, string> | null>({ title: "RU" });
  const session = ref("tenant:item:ru"),
    dirty = ref(false),
    reset = ref(0);
  let writes = 0;
  const draft = effects.run(() =>
    useProductContentDraft(
      () => source.value,
      () => session.value,
      () => dirty.value,
      () => {
        writes++;
        dirty.value = true;
      },
      () => reset.value,
    ),
  )!;
  draft.change("title", "Unsaved");
  reset.value++;
  await nextTick();
  assert.equal(draft.values.value.title, "RU");
  draft.change("body", "Old context");
  session.value = "other-tenant:item:uk";
  source.value = { title: "UK" };
  await nextTick();
  assert.deepEqual(draft.values.value, { title: "UK" });
  assert.equal(writes, 2);
  effects.stop();
});
