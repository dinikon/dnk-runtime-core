import type { EditorGroup } from "./product-editor-layout";

export type ProductEditorTab =
  "description" | "media" | "variants" | "publications";

/** Old section links still focus the same fields in the single editor. */
export function productEditorTab(
  value: unknown,
  variable: boolean,
  publications = true,
): ProductEditorTab {
  if (value === "media") return value;
  if (value === "publications" && publications) return value;
  if (value === "variants" && variable) return value;
  return "description";
}

export function productEditorGroup(value: unknown): EditorGroup | undefined {
  if (value === "inventory") return "stock";
  if (value === "shipping") return "measurements";
  if (value === "general") return "identity";
  return undefined;
}
