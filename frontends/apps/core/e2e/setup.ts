import { randomBytes } from "node:crypto";
import { runFixture } from "./fixture";

export default function setup() {
  process.env.CORE_E2E_PASSWORD = randomBytes(24).toString("base64url");
  process.env.CORE_E2E_SIGNUP_USERNAME = "core_e2e_passkey_" + randomBytes(6).toString("hex");
  runFixture("setup");
}
