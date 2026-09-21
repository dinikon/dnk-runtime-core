# Currency browser checks

Start Console with `npm run dev --workspace @dnk/console -- --port 5179` from
`frontends`. With Playwright and its Chromium browser available, run:

```sh
node frontends/apps/console/tests/browser/currency.mjs
```

`CURRENCY_UI_URL` overrides `http://127.0.0.1:5179`. `PLAYWRIGHT_MODULE` may point
to an existing Playwright installation when it is supplied by the development
runtime; otherwise the script resolves `playwright` normally. Install Chromium
with that installation's `playwright install chromium` command if needed.

The suite intercepts **only** `/api/` requests. It checks explicit initialization,
form defaults, period history, member access, empty provider/rate state, retained
409 drafts, intentional reload, personal preferences, inheritance and unavailable
preferences, manual revisions, future periods and exact formatting above JavaScript’s
safe integer limit. Real server authorization, decimal arithmetic, tenant scope and
transaction behavior are covered in the Python/isolated PostgreSQL tests.

The automation environment used the available Playwright runtime because the
purpose-built Browser plugin was unavailable. Screenshots are temporary artifacts;
`CURRENCY_SCREENSHOT` selects the history screenshot path.
