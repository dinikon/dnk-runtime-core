import type { SchemaCalculation, SchemaNode } from "./feed-schema.types.ts";
import type { NodeCategory, NodeKind } from "./feed-calculation.types.ts";
export const parameterTypes: Readonly<Record<string, string>> = {
  "price.regular": "number",
  "price.sale": "number",
  "price.effective": "number",
  "product.sku": "string",
  "product.id": "uuid",
};
export function initialCalculation(): SchemaCalculation {
  return {
    defaultExpression: { kind: "parameter", parameter: "price.regular" },
    rules: [],
    purchaseSource: null,
  };
}
export function newNode(
  kind: NodeKind,
  category: NodeCategory = "number",
): SchemaNode {
  const parameter: SchemaNode = {
      kind: "parameter",
      parameter: "price.regular",
    },
    zero: SchemaNode = { kind: "decimal", value: "0" };
  switch (kind) {
    case "decimal":
      return zero;
    case "parameter":
      return parameter;
    case "scalar":
      return { kind, valueType: "string", value: "" };
    case "collection":
      return {
        kind,
        itemType: "string",
        items: [{ kind: "scalar", valueType: "string", value: "" }],
      };
    case "arithmetic":
      return {
        kind,
        operator: "MULTIPLY",
        left: parameter,
        right: { kind: "decimal", value: "1" },
      };
    case "function":
      return { kind, function: "MAX", arguments: [parameter, zero] };
    case "comparison":
      return { kind, operator: "GTE", left: parameter, right: zero };
    case "presence":
      return { kind, operator: "EXISTS", parameter: "price.sale" };
    case "logical":
      return {
        kind,
        operator: "ALL",
        operands: [newNode("presence", category)],
      };
  }
}
export function nodeChildren(node: SchemaNode): SchemaNode[] {
  switch (node.kind) {
    case "arithmetic":
      return [node.left, node.right, node.operand].filter(
        (v): v is SchemaNode => !!v,
      );
    case "function":
      return node.arguments;
    case "comparison":
      return [node.left, node.right];
    case "logical":
      return node.operands;
    case "collection":
      return node.items;
    default:
      return [];
  }
}
export function calculationIsSupported(
  calculation: SchemaCalculation,
): boolean {
  if (calculation.purchaseSource) return false;
  const pending = [
    calculation.defaultExpression,
    ...calculation.rules.flatMap((r) => [r.condition, r.expression]),
  ];
  let count = 0;
  while (pending.length) {
    const node = pending.pop()!;
    // Незавершённый oversized draft должен оставаться редактируемым для исправления.
    if (++count > 4096) return true;
    if (
      (node.kind === "parameter" || node.kind === "presence") &&
      !parameterTypes[node.parameter]
    )
      return false;
    pending.push(...nodeChildren(node));
  }
  return true;
}
export function moveRule(
  calculation: SchemaCalculation,
  index: number,
  delta: number,
): SchemaCalculation {
  const next = index + delta;
  if (next < 0 || next >= calculation.rules.length) return calculation;
  const rules = [...calculation.rules],
    [rule] = rules.splice(index, 1);
  rules.splice(next, 0, rule!);
  return { ...calculation, rules };
}
export function quickExpression(
  base: string,
  operation: "percent" | "amount",
  value: string,
): SchemaNode {
  const amount: SchemaNode = { kind: "decimal", value };
  return operation === "amount"
    ? {
        kind: "arithmetic",
        operator: "ADD",
        left: { kind: "parameter", parameter: base },
        right: amount,
      }
    : {
        kind: "arithmetic",
        operator: "MULTIPLY",
        left: { kind: "parameter", parameter: base },
        right: {
          kind: "arithmetic",
          operator: "ADD",
          left: { kind: "decimal", value: "1" },
          right: {
            kind: "arithmetic",
            operator: "DIVIDE",
            left: amount,
            right: { kind: "decimal", value: "100" },
          },
        },
      };
}
