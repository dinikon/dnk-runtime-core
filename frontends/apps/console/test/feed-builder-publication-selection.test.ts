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
import type { usePublicationVariantSelection } from "../src/modules/feed-builder/model/use-publication-variant-selection.ts";
import type { usePublicationSelection } from "../src/modules/feed-builder/model/use-publication-selection.ts";
import type { PublicationChoice } from "../src/modules/feed-builder/model/feed-publication.types.ts";
const source = fileURLToPath(new URL("../src/", import.meta.url));
test("Variant snapshot rejects late ABA/closed/session responses while manual multi-page selection remains intact", async () => {
  const cacheDir = await mkdtemp(join(tmpdir(), "publication-selection-"));
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
    const { usePublicationVariantSelection: useSnapshot } =
      await server.ssrLoadModule(
        `${source}modules/feed-builder/model/use-publication-variant-selection.ts`,
      );
    const { usePublicationSelection: useSelection } =
      await server.ssrLoadModule(
        `${source}modules/feed-builder/model/use-publication-selection.ts`,
      );
    const { feedPublicationApi } = await server.ssrLoadModule(
      `${source}modules/feed-builder/api/feed-publication.api.ts`,
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
    const calls: {
      signal: AbortSignal;
      resolve: (value: PublicationChoice[]) => void;
      reject: (error: unknown) => void;
    }[] = [];
    feedPublicationApi.variants = (
      _feed: string,
      _root: string,
      _locale: string,
      signal: AbortSignal,
    ): Promise<PublicationChoice[]> =>
      new Promise((resolve, reject) => calls.push({ signal, resolve, reject }));
    let snapshot!: ReturnType<typeof usePublicationVariantSelection>,
      selection!: ReturnType<typeof usePublicationSelection>;
    const root = ref("A"),
      context = ref("open");
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
          snapshot = useSnapshot(ref("feed"), root, ref("uk"), context);
          selection = useSelection();
          return () => null;
        },
      }),
    );
    app.use(pinia);
    app.use(VueQueryPlugin, { queryClient: client });
    app.mount({});
    unmount = () => app.unmount();
    const white: PublicationChoice = {
      itemId: "A",
      variantId: "white",
      title: "White",
      sku: "W",
      kind: "variant",
    };
    selection.toggle(white);
    selection.search.value = "different page";
    selection.offset.value = 20;
    await nextTick();
    assert.deepEqual(
      selection.selected.value.map((v) => v.variantId),
      ["white"],
    );
    const old = snapshot.execute();
    assert.equal(snapshot.pending.value, true);
    assert.equal(await snapshot.execute(), undefined);
    assert.equal(calls.length, 1);
    root.value = "B";
    root.value = "A";
    assert.equal(calls[0]!.signal.aborted, true);
    calls[0]!.resolve([white]);
    assert.equal(await old, undefined);
    const closed = snapshot.execute();
    context.value = "closed";
    calls[1]!.resolve([white]);
    assert.equal(await closed, undefined);
    assert.equal(snapshot.pending.value, false);
    context.value = "open";
    const changed = snapshot.execute();
    tenant.tenant = { ...tenant.tenant, tenant_id: "b" };
    calls[2]!.reject(new Error("late source failure"));
    assert.equal(await changed, undefined);
    assert.equal(snapshot.error.value, undefined);
    const accepted = snapshot.execute();
    calls[3]!.resolve([white, { ...white, variantId: "black", sku: "B" }]);
    selection.merge((await accepted)!);
    assert.deepEqual(
      selection.selected.value.map((v) => v.variantId),
      ["white", "black"],
    );
    user.setUser(null);
    assert.equal(await snapshot.execute(), undefined);
    selection.reset();
    assert.deepEqual(selection.selected.value, []);
  } finally {
    unmount();
    client.clear();
    await server.close();
    await rm(cacheDir, { recursive: true, force: true });
  }
});
