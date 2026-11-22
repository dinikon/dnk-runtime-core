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
import { schemaMetadata, fourFieldSchema } from "./feed-schema-support.ts";
import { fieldDraft } from "../src/modules/feed-builder/model/feed-schema.draft.ts";
import { mapPreview } from "../src/modules/feed-builder/api/feed-calculation.mapper.ts";
import { previewDTO } from "./feed-calculation-support.ts";
import type {
  CalculationPreview,
  PreviewRequest,
} from "../src/modules/feed-builder/model/feed-calculation.types.ts";
import type { useFeedCalculationPreview } from "../src/modules/feed-builder/model/use-feed-calculation-preview.ts";
const source = fileURLToPath(new URL("../src/", import.meta.url));
async function settle(): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, 15));
  await nextTick();
}

test("Preview ignores late responses after ABA edits, source/version/identity changes; never invalidates writes and expires at sale boundary", async () => {
  const cacheDir = await mkdtemp(join(tmpdir(), "feed-price-preview-"));
  const server = await createServer({
    configFile: false,
    cacheDir,
    optimizeDeps: { noDiscovery: true, include: [] },
    logLevel: "silent",
    resolve: { alias: { "@": source } },
    plugins: [
      {
        name: "catalog-public-test-contract",
        enforce: "pre",
        resolveId(id) {
          if (id === "@/modules/catalog") return "\0catalog-preview-test";
        },
        load(id) {
          if (
            id === "\0catalog-preview-test" ||
            id === `${source}modules/catalog/index.ts`
          )
            return "export async function searchCatalogPreviewProducts(){ return {items:[],total:0}; } export async function searchCatalogPreviewVariants(){ return {items:[],total:0}; }";
        },
      },
    ],
    server: { middlewareMode: true },
  });
  const client = new QueryClient({
      defaultOptions: { queries: { retry: false, gcTime: 0 } },
    }),
    pinia = createPinia();
  let unmount = (): void => {};
  try {
    const module = await server.ssrLoadModule(
      `${source}modules/feed-builder/model/use-feed-calculation-preview.ts`,
    );
    const { feedCalculationApi } = await server.ssrLoadModule(
      `${source}modules/feed-builder/api/feed-calculation.api.ts`,
    );
    const { useTenantStore } = await server.ssrLoadModule(
        `${source}app/stores/tenant.ts`,
      ),
      { useUserStore } = await server.ssrLoadModule(
        `${source}app/stores/user.ts`,
      );
    const tenant = useTenantStore(pinia),
      user = useUserStore(pinia);
    tenant.tenant = { tenant_id: "a", exists: true, available: true };
    user.setUser({ id: "actor", emails: [] });
    feedCalculationApi.metadata = async () => ({
      parameters: [],
      operations: [],
      engineVersion: "1",
      precision: 40,
      maxDepth: 32,
      maxNodes: 4096,
      maxRules: 100,
      maxCollectionItems: 500,
    });
    const calls: {
      signal: AbortSignal;
      value: PreviewRequest;
      resolve: (value: CalculationPreview) => void;
      reject: (error: unknown) => void;
    }[] = [];
    feedCalculationApi.preview = (
      value: PreviewRequest,
      signal: AbortSignal,
    ): Promise<CalculationPreview> =>
      new Promise((resolve, reject) =>
        calls.push({ value, signal, resolve, reject }),
      );
    let preview!: ReturnType<typeof useFeedCalculationPreview>;
    const field = ref(fieldDraft(fourFieldSchema().fields[3]!)),
      version = ref<number | null>(7),
      blocked = ref(false);
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
          preview = module.useFeedCalculationPreview(
            ref("feed"),
            version,
            field,
            ref(schemaMetadata),
            blocked,
          );
          return () => null;
        },
      }),
    );
    app.use(pinia);
    app.use(VueQueryPlugin, { queryClient: client });
    app.mount({});
    unmount = () => app.unmount();
    await settle();
    preview.root.value = {
      id: "item",
      title: "Товар",
      sku: "ONE",
      kind: "simple",
    };
    assert.equal(preview.canPreview.value, true);
    const first = preview.preview();
    assert.equal(calls.length, 1);
    assert.equal(preview.pending.value, true);
    await preview.preview();
    assert.equal(calls.length, 1);
    const label = field.value.label;
    field.value.label = "New";
    field.value.label = label;
    assert.equal(calls[0]!.signal.aborted, true);
    assert.equal(preview.pending.value, false);
    calls[0]!.resolve(mapPreview(previewDTO));
    await first;
    assert.equal(preview.result.value, null);
    const second = preview.preview();
    calls[1]!.resolve(mapPreview(previewDTO));
    await second;
    assert.equal(preview.stale.value, false);
    assert.equal(
      preview.result.value?.resolvedValue?.amount,
      previewDTO.resolved_value!.amount,
    );
    assert.equal(
      client
        .getQueryCache()
        .getAll()
        .some((q) => q.state.isInvalidated),
      false,
    );
    version.value = 8;
    assert.equal(preview.stale.value, true);
    const third = preview.preview();
    assert.equal(calls[2]!.value.expectedVersion, 8);
    calls[2]!.resolve({
      ...mapPreview(previewDTO),
      version: 8,
      validUntil: new Date(Date.now() + 30).toISOString(),
    });
    await third;
    await new Promise((resolve) => setTimeout(resolve, 45));
    assert.equal(preview.stale.value, true);
    preview.root.value = {
      id: "family",
      title: "Family",
      sku: null,
      kind: "variable",
    };
    assert.equal(preview.canPreview.value, false);
    preview.variant.value = {
      id: "white",
      title: "White",
      sku: "WHITE",
      kind: "variant",
    };
    assert.equal(preview.canPreview.value, true);
    const fourth = preview.preview();
    assert.equal(calls[3]!.value.variantId, "white");
    tenant.tenant = { ...tenant.tenant, tenant_id: "b" };
    await settle();
    assert.equal(calls[3]!.signal.aborted, true);
    assert.equal(preview.root.value, null);
    assert.equal(preview.result.value, null);
    calls[3]!.resolve(mapPreview(previewDTO));
    await fourth;
    assert.equal(preview.result.value, null);
    preview.root.value = {
      id: "item",
      title: "Other tenant",
      sku: null,
      kind: "simple",
    };
    const fifth = preview.preview();
    user.setUser(null);
    await settle();
    assert.equal(calls[4]!.signal.aborted, true);
    assert.equal(preview.canPreview.value, false);
    assert.equal(preview.result.value, null);
    calls[4]!.reject(new Error("Late old error"));
    await fifth;
    assert.equal(preview.error.value, undefined);
  } finally {
    unmount();
    client.clear();
    await server.close();
    await rm(cacheDir, { recursive: true, force: true });
  }
});
