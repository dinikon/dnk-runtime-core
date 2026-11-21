import { after, before, test } from "node:test";
import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";
import { createServer, type ViteDevServer } from "vite";

let server: ViteDevServer;
let fileError: (cause: unknown) => string;
before(async () => {
  server = await createServer({
    configFile: false,
    optimizeDeps: { noDiscovery: true },
    server: { middlewareMode: true, hmr: false, ws: false },
    resolve: {
      alias: { "@": fileURLToPath(new URL("../src", import.meta.url)) },
    },
  });
  ({ fileError } = await server.ssrLoadModule(
    "/src/modules/files/model/errors.ts",
  ));
});
after(async () => server?.close());

test("used file explains its references while other conflicts retain their meaning", () => {
  const error = {
    isAxiosError: true,
    response: { status: 409, data: { detail: { code: "file_in_use" } } },
  };
  assert.match(fileError(error), /галерей каталога и каналов/);
  assert.match(
    fileError({
      ...error,
      response: { status: 409, data: { detail: { code: "state_changed" } } },
    }),
    /Состояние файла или диска изменилось/,
  );
  assert.match(
    fileError({
      ...error,
      response: { status: 403, data: error.response.data },
    }),
    /Недостаточно прав/,
  );
});
