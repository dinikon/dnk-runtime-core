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
import { fourFieldSchema, schemaMetadata } from "./feed-schema-support.ts";
import type {
  FeedSchema,
  SavedFeedSchema,
} from "../src/modules/feed-builder/model/feed-schema.types.ts";
import type { FeedSchemaEditor } from "../src/modules/feed-builder/model/use-feed-schema-editor.ts";
const source = fileURLToPath(new URL("../src/", import.meta.url));
async function settle(): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, 15));
  await nextTick();
}

test("Schema editor preserves drafts on refetch and CAS conflicts, acknowledges sent snapshot and clears identity data", async () => {
  const cacheDir = await mkdtemp(join(tmpdir(), "feed-schema-test-"));
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
    }),
    pinia = createPinia();
  let unmount = (): void => {};
  try {
    const { useFeedSchemaEditor } = await server.ssrLoadModule(
      `${source}modules/feed-builder/model/use-feed-schema-editor.ts`,
    );
    const { feedSchemaApi } = await server.ssrLoadModule(
      `${source}modules/feed-builder/api/feed-schema.api.ts`,
    );
    const { useTenantStore } = await server.ssrLoadModule(
      `${source}app/stores/tenant.ts`,
    );
    const { useUserStore } = await server.ssrLoadModule(
      `${source}app/stores/user.ts`,
    );
    const { SchemaApiError } = await server.ssrLoadModule(
      `${source}modules/feed-builder/model/feed-schema.types.ts`,
    );
    const tenant = useTenantStore(pinia),
      user = useUserStore(pinia);
    tenant.tenant = { tenant_id: "a", exists: true, available: true };
    user.setUser({ id: "actor", emails: [] });
    let stored: FeedSchema = {
      feedId: "one",
      version: 1,
      status: "DRAFT",
      definition: fourFieldSchema(),
    };
    let resolveSave: ((value: SavedFeedSchema) => void) | undefined,
      calls = 0,
      conflict = false;
    feedSchemaApi.get = async (): Promise<FeedSchema> =>
      structuredClone(stored);
    feedSchemaApi.metadata = async () => structuredClone(schemaMetadata);
    feedSchemaApi.save = async (): Promise<SavedFeedSchema> => {
      calls++;
      if (conflict) throw new SchemaApiError(409, []);
      return new Promise((resolve) => {
        resolveSave = resolve;
      });
    };
    let editor!: FeedSchemaEditor;
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
          editor = useFeedSchemaEditor(ref("one"));
          return () => null;
        },
      }),
    );
    app.use(pinia);
    app.use(VueQueryPlugin, { queryClient: client });
    app.mount({});
    unmount = () => app.unmount();
    await settle();
    assert.equal(editor.draft.value?.fields.length, 4);
    assert.equal(editor.dirty.value, false);
    editor.draft.value!.fields[0]!.label = "Local input";
    stored = {
      ...stored,
      version: 2,
      definition: structuredClone(stored.definition),
    };
    stored.definition.fields[0]!.label = "Remote input";
    await editor.query.refetch();
    await settle();
    assert.equal(editor.draft.value!.fields[0]!.label, "Local input");
    assert.equal(editor.conflict.value, true);
    assert.equal(await editor.save(), false);
    assert.equal(calls, 0);
    editor.reset();
    assert.equal(editor.draft.value!.fields[0]!.label, "Remote input");
    editor.draft.value!.fields[0]!.label = "Sent";
    const saving = editor.save();
    await nextTick();
    assert.equal(editor.busy.value, true);
    assert.equal(await editor.save(), false);
    editor.draft.value!.fields[0]!.label = "Typed after submit";
    stored = {
      ...stored,
      version: 3,
      definition: structuredClone(stored.definition),
    };
    stored.definition.fields[0]!.label = "Sent";
    resolveSave!(structuredClone(stored));
    assert.equal(await saving, true);
    await settle();
    assert.equal(editor.draft.value!.fields[0]!.label, "Typed after submit");
    assert.equal(editor.dirty.value, true);
    assert.equal(calls, 1);
    conflict = true;
    assert.equal(await editor.save(), false);
    assert.equal(editor.conflict.value, true);
    assert.equal(editor.draft.value!.fields[0]!.label, "Typed after submit");
    editor.reset();
    conflict = false;
    editor.draft.value!.fields[0]!.label = "Old tenant mutation";
    const pending = editor.save();
    await nextTick();
    const finishOld = resolveSave!;
    tenant.tenant = { ...tenant.tenant, tenant_id: "b" };
    await settle();
    assert.equal(editor.draft.value!.fields[0]!.label, "Sent");
    assert.equal(editor.busy.value, false);
    finishOld({ ...structuredClone(stored), version: 4 });
    assert.equal(await pending, false);
    await settle();
    assert.equal(editor.draft.value!.fields[0]!.label, "Sent");
    assert.equal(
      client
        .getQueryCache()
        .getAll()
        .some((q) => q.queryKey[1] === "a"),
      false,
    );
    stored = { ...stored, status: "ARCHIVED", version: 4 };
    await editor.query.refetch();
    await settle();
    assert.equal(editor.readonly.value, true);
    const before = calls;
    assert.equal(await editor.save(), false);
    assert.equal(calls, before);
    const count = editor.draft.value!.fields.length;
    editor.add("string");
    editor.remove(editor.draft.value!.fields[0]!.id);
    assert.equal(editor.draft.value!.fields.length, count);
    user.clearUser();
    await settle();
    assert.equal(editor.draft.value, null);
    assert.equal(
      client
        .getQueryCache()
        .getAll()
        .some((q) => q.queryKey[2] === "actor"),
      false,
    );
  } finally {
    unmount();
    client.clear();
    await server.close();
    await rm(cacheDir, { recursive: true, force: true });
  }
});
