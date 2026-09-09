import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

type FixtureRole = "member" | "staff" | "superuser";

export function runFixture(
  operation: "setup" | "cleanup" | "mail" | "login-mail" | "reset" | "navigation" | "inspect" | "phone-code" | "phones",
  options: { role?: FixtureRole } = {},
) {
  const args = ["compose", "exec", "-T", "-e", `CORE_E2E_OPERATION=${operation}`];
  args.push("-e", "CORE_E2E_SIGNUP_USERNAME");
  if (options.role) args.push("-e", `CORE_E2E_ROLE=${options.role}`);
  if (operation === "setup" || operation === "reset") args.push("-e", "CORE_E2E_PASSWORD");
  args.push("core", "python", "src/manage.py", "shell", "--no-imports");
  const output = execFileSync("docker", args, {
    cwd: fileURLToPath(new URL("../../../../", import.meta.url)),
    input: readFileSync(new URL("fixture_account.py", import.meta.url), "utf8"),
    env: process.env,
    stdio: ["pipe", "pipe", "pipe"],
    encoding: "utf8",
  });
  return JSON.parse(output.trim().split("\n").at(-1)!);
}
