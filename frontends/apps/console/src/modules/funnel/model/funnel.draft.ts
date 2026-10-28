import type { FunnelDraft, FunnelStageDraft, StageKind } from "./funnel.types";

export const stageGroups: readonly { kind: StageKind; label: string }[] = [
  { kind: "in_progress", label: "В работе" },
  { kind: "won", label: "Успешные" },
  { kind: "lost", label: "Неуспешные" },
];
export const stagePalette = [
  "#64748B",
  "#3B82F6",
  "#06B6D4",
  "#22C55E",
  "#84CC16",
  "#F59E0B",
  "#EF4444",
  "#8B5CF6",
] as const;
export function defaultFunnelDraft(
  modelKey: FunnelDraft["modelKey"],
): FunnelDraft {
  return {
    name: "",
    modelKey,
    stages: [
      { name: "Новый", kind: "in_progress", color: "#3B82F6" },
      { name: "В работе", kind: "in_progress", color: "#06B6D4" },
      { name: "Успешный", kind: "won", color: "#84CC16" },
      { name: "Неудачный", kind: "lost", color: "#EF4444" },
    ].map((s) => ({
      ...s,
      kind: s.kind as StageKind,
      clientKey: crypto.randomUUID(),
    })),
  };
}
export function canRemoveStage(
  stages: FunnelStageDraft[],
  key: string,
): boolean {
  const stage = stages.find((s) => s.clientKey === key);
  return (
    !!stage &&
    stage.kind !== "won" &&
    stages.filter((s) => s.kind === stage.kind).length > 1
  );
}
export function moveStage(
  stages: FunnelStageDraft[],
  from: number,
  to: number,
): FunnelStageDraft[] {
  if (
    from < 0 ||
    to < 0 ||
    from >= stages.length ||
    to >= stages.length ||
    stages[from]!.kind !== stages[to]!.kind
  )
    return stages;
  const result = [...stages];
  result.splice(to, 0, result.splice(from, 1)[0]!);
  return result;
}
export function validateFunnelDraft(draft: FunnelDraft): string {
  if (!draft.name.trim() || draft.stages.some((s) => !s.name.trim()))
    return "Заполните название воронки и всех стадий.";
  if (draft.stages.some((s) => !/^#[0-9a-fA-F]{6}$/.test(s.color)))
    return "Укажите цвет каждой стадии в формате #RRGGBB.";
  const kinds = draft.stages.map((s) => s.kind);
  if (
    kinds.length < 3 ||
    kinds.length > 50 ||
    kinds.filter((k) => k === "won").length !== 1 ||
    !kinds.includes("in_progress") ||
    !kinds.includes("lost")
  )
    return "Нужны 3–50 стадий: рабочие, одна успешная и неуспешные.";
  const order = { in_progress: 0, won: 1, lost: 2 };
  if (kinds.some((kind, i) => i > 0 && order[kinds[i - 1]!] > order[kind]))
    return "Проверьте порядок групп стадий.";
  return "";
}

/** Acknowledge only the submitted values, retaining edits made during refetch. */
export function acknowledgeFunnelDraft(
  current: FunnelDraft,
  sent: FunnelDraft,
  stageIdMap: Record<string, string>,
): { current: FunnelDraft; baseline: FunnelDraft } {
  const baseline: FunnelDraft = {
    ...sent,
    name: sent.name.trim(),
    stages: sent.stages.map((stage) => ({
      ...stage,
      id: stage.id ?? stageIdMap[stage.clientKey],
      name: stage.name.trim(),
      color: stage.color.toUpperCase(),
    })),
  };
  return {
    baseline,
    current: {
      ...current,
      name: current.name === sent.name ? baseline.name : current.name,
      stages: current.stages.map((stage) => {
        const index = sent.stages.findIndex(
          (value) => value.clientKey === stage.clientKey,
        );
        if (index < 0) return stage;
        const submitted = sent.stages[index]!;
        const saved = baseline.stages[index]!;
        return {
          ...stage,
          id: saved.id,
          name: stage.name === submitted.name ? saved.name : stage.name,
          color: stage.color === submitted.color ? saved.color : stage.color,
        };
      }),
    },
  };
}
