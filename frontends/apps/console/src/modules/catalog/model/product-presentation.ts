export { statusLabels, stockLabels } from "./product-labels.ts";

/** Выбирает поля формы; эффективное наличие по-прежнему вычисляет Backend. */
export function stockFormMode(
  kind: "simple" | "variable" | "variant",
  own: import("./product.types").ProductStock,
  parent?: import("./product.types").ProductStock,
): "quantity" | "manual" | "inherited" | "variants" {
  if (own.manage_stock) return "quantity";
  if (kind === "variable") return "variants";
  return kind === "variant" && parent?.manage_stock ? "inherited" : "manual";
}
