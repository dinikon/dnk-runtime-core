import { test } from "node:test";
import assert from "node:assert/strict";
import {
  defaultFunnelDraft,
  canRemoveStage,
  moveStage,
  validateFunnelDraft,
} from "../src/modules/funnel/model/funnel.draft.ts";

test("Template has exactly one won and required work/lost groups", () => {
  const draft = defaultFunnelDraft("crm.deal");
  draft.name = "Sales";
  assert.deepEqual(
    draft.stages.map((s) => s.kind),
    ["in_progress", "in_progress", "won", "lost"],
  );
  assert.equal(validateFunnelDraft(draft), "");
  assert.equal(canRemoveStage(draft.stages, draft.stages[0]!.clientKey), true);
  assert.equal(canRemoveStage(draft.stages, draft.stages[2]!.clientKey), false);
  assert.equal(canRemoveStage(draft.stages, draft.stages[3]!.clientKey), false);
});
test("Reordering stays in its group and never changes source values", () => {
  const { stages } = defaultFunnelDraft("crm.lead");
  const moved = moveStage(stages, 0, 1);
  assert.equal(moved[0], stages[1]);
  assert.equal(stages[0]!.name, "Новый");
  assert.equal(moveStage(stages, 0, 3), stages);
});
test("Invalid hex and missing terminal groups are rejected", () => {
  const draft = defaultFunnelDraft("crm.lead");
  draft.name = "Sales";
  draft.stages[0]!.color = "#fff";
  assert.match(validateFunnelDraft(draft), /RRGGBB/);
  draft.stages[0]!.color = "#abcdef";
  assert.equal(validateFunnelDraft(draft), "");
  draft.stages.pop();
  assert.notEqual(validateFunnelDraft(draft), "");
});

test("Save acknowledgement assigns IDs without losing later input", async () => {
  const { acknowledgeFunnelDraft } =
    await import("../src/modules/funnel/model/funnel.draft.ts");
  const sent = defaultFunnelDraft("crm.deal");
  sent.name = " Sales ";
  const current = structuredClone(sent);
  current.name = "Typed later";
  current.stages[0]!.name = "Later stage name";
  const ids = Object.fromEntries(
    sent.stages.map((stage, i) => [stage.clientKey, "s" + i]),
  );
  const ack = acknowledgeFunnelDraft(current, sent, ids);
  assert.equal(ack.current.name, "Typed later");
  assert.equal(ack.current.stages[0]!.name, "Later stage name");
  assert.equal(ack.current.stages[0]!.id, "s0");
  assert.equal(ack.baseline.name, "Sales");
  assert.notDeepEqual(ack.current, ack.baseline);
});
