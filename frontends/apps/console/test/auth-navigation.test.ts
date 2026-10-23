import assert from "node:assert/strict";
import test from "node:test";
import {
  requestsCloudLogin,
  withoutAuthProvider,
} from "../src/modules/auth/model/cloud-navigation.ts";

test("only one exact provider hint triggers cloud login", () => {
  assert.equal(requestsCloudLogin("cloud"), true);
  for (const hint of [
    undefined,
    null,
    "",
    "other",
    ["cloud"],
    ["cloud", "cloud"],
  ]) {
    assert.equal(requestsCloudLogin(hint), false);
  }
});

test("consuming a cloud hint preserves the destination, other query parameters and fragment", () => {
  assert.equal(
    withoutAuthProvider("/dashboard?auth_provider=cloud&tab=recent#item"),
    "/dashboard?tab=recent#item",
  );
  assert.equal(withoutAuthProvider("/?auth_provider=cloud"), "/");
  assert.equal(
    withoutAuthProvider("/login?auth_provider=cloud&auth_provider=cloud"),
    "/login",
  );
  assert.equal(
    withoutAuthProvider("/settings/account?tab=profile"),
    "/settings/account?tab=profile",
  );
});
