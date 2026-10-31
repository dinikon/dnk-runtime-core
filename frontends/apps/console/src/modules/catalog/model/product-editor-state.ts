import type { EditorGroup } from "./product-editor-layout";

export type ProductEditorTab = "description" | "variants";

/** Old section links still focus the same fields in the single editor. */
export function productEditorTab(
  value: unknown,
  variable: boolean,
): ProductEditorTab {
  if (value === "variants" && variable) return value;
  return "description";
}

export function productEditorGroup(value: unknown): EditorGroup | undefined {
  if (value === "media") return "media";
  if (value === "inventory") return "stock";
  if (value === "shipping") return "measurements";
  if (value === "general") return "identity";
  return undefined;
}
