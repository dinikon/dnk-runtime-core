import { test } from "node:test";
import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createServer } from "vite";
import { createRenderer, defineComponent, ref, nextTick } from "vue";
import { createPinia } from "pinia";
import { VueQueryPlugin, QueryClient } from "@tanstack/vue-query";
import type { Feed } from "../src/modules/feed-builder/model/feed.types.ts";
import type { FeedEditor } from "../src/modules/feed-builder/model/use-feed-editor.ts";

const source = fileURLToPath(new URL("../src/", import.meta.url));
const original: Feed = {
  id: "one",
  name: "Retail",
  code: "retail",
  status: "DRAFT",
  version: 1,
  createdAt: "2026-11-22T10:00:00Z",
  updatedAt: "2026-11-22T10:00:00Z",
  schema: { root: { fields: [] } },
  exportSettings: {
    formatSettings: {
      format: "csv",
      delimiter: ",",
      includeHeader: true,
      encoding: "utf-8",
    },
    productMode: "VARIABLE_TO_SINGLE",
    validationPolicy: "STRICT",
  },
};
async function settle(): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, 15));
  await nextTick();
}
test("Editor keeps dirty input on refetch/conflict, adopts only acknowledged data and isolates scope changes", async () => {
  // Vite resolves the same application aliases used by the browser, without a DOM or another test framework.
  const cacheDir = await mkdtemp(join(tmpdir(), "feed-builder-test-"));
  const server = await createServer({
    configFile: false,
    cacheDir,
    optimizeDeps: { noDiscovery: true, include: [] },
    logLevel: "silent",
    resolve: { alias: { "@": source } },
    server: { middlewareMode: true },
  });
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  const pinia = createPinia();
  let unmount = (): void => {};
  try {
    const { useFeedEditor } = await server.ssrLoadModule(
      `${source}modules/feed-builder/model/use-feed-editor.ts`,
    );
    const { feedApi } = await server.ssrLoadModule(
      `${source}modules/feed-builder/api/feed.api.ts`,
    );
    const { useTenantStore } = await server.ssrLoadModule(
      `${source}app/stores/tenant.ts`,
    );
    const { useUserStore } = await server.ssrLoadModule(
      `${source}app/stores/user.ts`,
    );
    const { FeedApiError } = await server.ssrLoadModule(
      `${source}modules/feed-builder/model/feed.types.ts`,
    );
    const tenant = useTenantStore(pinia),
      user = useUserStore(pinia);
    tenant.tenant = { tenant_id: "a", exists: true, available: true };
    user.setUser({ id: "actor", emails: [] });
    let stored = structuredClone(original),
      updateCalls = 0,
      rejectConflict = false;
    let resolveSave: ((value: Feed) => void) | undefined;
    feedApi.get = async (): Promise<Feed> => structuredClone(stored);
    feedApi.update = async (): Promise<Feed> => {
      updateCalls++;
      if (rejectConflict) throw new FeedApiError(409);
      return new Promise((resolve) => {
        resolveSave = resolve;
      });
    };
    let editor!: FeedEditor;
    const renderer = createRenderer({
      createElement: () => ({}),
      createText: () => ({}),
      createComment: () => ({}),
      insert: () => {},
      remove: () => {},
      setText: () => {},
      setElementText: () => {},
      parentNode: () => null,
      nextSibling: () => null,
      patchProp: () => {},
    });
    const app = renderer.createApp(
      defineComponent({
        setup() {
          editor = useFeedEditor(ref("one"));
          return () => null;
        },
      }),
    );
    app.use(pinia);
    app.use(VueQueryPlugin, { queryClient: client });
    app.mount({});
    unmount = () => app.unmount();
    await settle();
    assert.equal(editor.draft.value?.name, "Retail");
    editor.draft.value!.name = " Retail ";
    assert.equal(await editor.save(), "one");
    assert.equal(editor.dirty.value, false);
    assert.equal(updateCalls, 0);
    editor.draft.value!.name = "My draft";
    stored = { ...stored, name: "Remote change", version: 2 };
    await editor.query.refetch();
    await settle();
    assert.equal(editor.draft.value?.name, "My draft");
    assert.equal(editor.base.value?.version, 1);
    assert.equal(editor.conflict.value, true);
    assert.equal(await editor.save(), undefined);
    assert.equal(updateCalls, 0);
    editor.reset();
    assert.equal(editor.draft.value?.name, "Remote change");
    assert.equal(editor.base.value?.version, 2);
    editor.draft.value!.name = "Sent snapshot";
    const saving = editor.save();
    await nextTick();
    assert.equal(editor.busy.value, true);
    assert.equal(await editor.save(), undefined);
    editor.draft.value!.name = "Typed while saving";
    stored = { ...stored, name: "Sent snapshot", version: 3 };
    resolveSave!(structuredClone(stored));
    await saving;
    await settle();
    assert.equal(updateCalls, 1);
    assert.equal(editor.draft.value?.name, "Typed while saving");
    assert.equal(editor.base.value?.version, 3);
    assert.equal(editor.dirty.value, true);
    rejectConflict = true;
    await editor.save();
    await settle();
    assert.equal(editor.conflict.value, true);
    assert.equal(editor.draft.value?.name, "Typed while saving");
    assert.equal(editor.base.value?.version, 3);
    editor.reset();
    rejectConflict = false;
    editor.draft.value!.name = "Old tenant request";
    const old = editor.save();
    await nextTick();
    const finishOld = resolveSave!;
    tenant.tenant = { ...tenant.tenant, tenant_id: "b" };
    await settle();
    assert.equal(editor.draft.value?.name, "Sent snapshot");
    assert.equal(editor.dirty.value, false);
    assert.equal(editor.busy.value, false);
    finishOld({ ...stored, name: "Late old tenant result", version: 4 });
    assert.equal(await old, undefined);
    await settle();
    assert.equal(editor.draft.value?.name, "Sent snapshot");
    assert.equal(
      client
        .getQueryCache()
        .getAll()
        .some((query) => query.queryKey[1] === "a"),
      false,
    );
    stored = { ...stored, status: "ARCHIVED", version: 4 };
    await editor.query.refetch();
    await settle();
    assert.equal(editor.readonly.value, true);
    editor.draft.value!.name = "Must not send";
    const before = updateCalls;
    await editor.save();
    assert.equal(updateCalls, before);
    user.clearUser();
    await settle();
    assert.equal(editor.draft.value, null);
    assert.equal(
      client
        .getQueryCache()
        .getAll()
        .some((query) => query.queryKey[2] === "actor"),
      false,
    );
  } finally {
    unmount();
    client.clear();
    await server.close();
    await rm(cacheDir, { recursive: true, force: true });
  }
});
