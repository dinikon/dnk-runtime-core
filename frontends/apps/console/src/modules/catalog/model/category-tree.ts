import type {
  CatalogCategory,
  CategoryOption,
  CategorySelection,
} from "./category.types";

/** Устойчивый к глубине обход: родитель всегда расположен перед детьми. */
export function categoryTree(rows: CatalogCategory[]): CategoryOption[] {
  const children = new Map<string | null, CatalogCategory[]>();
  for (const row of rows) {
    const branch = children.get(row.parentId);
    if (branch) branch.push(row);
    else children.set(row.parentId, [row]);
  }
  const stack = (children.get(null) ?? [])
    .map((row) => ({ row, parentPath: "", depth: 0 }))
    .reverse();
  const result: CategoryOption[] = [];
  while (stack.length) {
    const { row, parentPath, depth } = stack.pop()!;
    const label =
      row.name ?? `${row.fallbackName} (${row.fallbackLocale}, нет перевода)`;
    const path = parentPath ? parentPath + " / " + label : label;
    result.push({ ...row, path, depth });
    for (const child of [...(children.get(row.id) ?? [])].reverse())
      stack.push({ row: child, parentPath: path, depth: depth + 1 });
  }
  return result;
}

export function withSelectedCategories(
  selection: CategorySelection,
  selectedIds: readonly string[],
): CategorySelection {
  const additionalIds = new Set(selectedIds);
  additionalIds.delete(selection.primary_category_id);
  return {
    primary_category_id: selection.primary_category_id,
    additional_category_ids: [...additionalIds],
  };
}

export function choosePrimary(
  selection: CategorySelection,
  id: string,
): CategorySelection {
  const additional = selection.additional_category_ids;
  return {
    primary_category_id: id,
    additional_category_ids: additional.includes(id)
      ? [
          ...additional.filter((other) => other !== id),
          selection.primary_category_id,
        ]
      : [...additional],
  };
}
