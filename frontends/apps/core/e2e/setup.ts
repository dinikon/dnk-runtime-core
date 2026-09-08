import { randomBytes } from "node:crypto";
import { runFixture } from "./fixture";

export default function setup() {
  process.env.CORE_E2E_PASSWORD = randomBytes(24).toString("base64url");
  runFixture("setup");
}
