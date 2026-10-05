import { computed, type Ref } from "vue";
import { useQuery, type QueryClient } from "@tanstack/vue-query";
import { getApiErrorMessage, getApiErrorStatus } from "@/app/providers/http";
import { categoriesApi } from "../api/categories.api";
import type { CategoryListDto } from "../api/contracts";
import { useCatalogTenant } from "./queries";
import { isUuid } from "./forms";
export const categoryKeys = {
  all: (tenant: string) => ["catalog", tenant, "categories"] as const,
  list: (tenant: string, locale: string) =>
    ["catalog", tenant, "categories", "list", locale] as const,
  detail: (tenant: string, id: string, locale: string) =>
    ["catalog", tenant, "categories", "detail", id, locale] as const,
};
export function useCategories(locale: Ref<string>) {
  const tenant = useCatalogTenant();
  return useQuery({
    queryKey: computed(() => categoryKeys.list(tenant.value, locale.value)),
    queryFn: ({ signal }) => categoriesApi.list(locale.value, signal),
    enabled: computed(() => !!locale.value),
    retry: false,
  });
}
export function useCategory(id: Ref<string>, locale: Ref<string>) {
  const tenant = useCatalogTenant();
  return useQuery({
    queryKey: computed(() =>
      categoryKeys.detail(tenant.value, id.value, locale.value),
    ),
    queryFn: ({ signal }) => categoriesApi.get(id.value, locale.value, signal),
    enabled: computed(() => isUuid(id.value) && !!locale.value),
    retry: false,
  });
}
export async function invalidateCategories(
  client: QueryClient,
  tenant: string,
) {
  await Promise.all([
    client.invalidateQueries({ queryKey: categoryKeys.all(tenant) }),
    client.invalidateQueries({ queryKey: ["catalog", tenant, "product"] }),
  ]);
}
export const categoryLabel = (item: { id: string; name: string | null }) =>
  item.name ?? `Без перевода — ${item.id}`;
export function descendants(items: CategoryListDto[], id: string) {
  const result = new Set([id]);
  let changed = true;
  while (changed) {
    changed = false;
    for (const item of items)
      if (
        item.parent_id &&
        result.has(item.parent_id) &&
        !result.has(item.id)
      ) {
        result.add(item.id);
        changed = true;
      }
  }
  return result;
}
export interface CategoryNode extends CategoryListDto {
  children: CategoryNode[];
}
export function categoryTree(items: CategoryListDto[]): CategoryNode[] {
  const nodes = new Map(
    items.map((item) => [item.id, { ...item, children: [] } as CategoryNode]),
  );
  const roots: CategoryNode[] = [];
  for (const node of nodes.values()) {
    const parent = node.parent_id ? nodes.get(node.parent_id) : undefined;
    if (parent && parent !== node) parent.children.push(node);
    else roots.push(node);
  }
  const sort = (list: CategoryNode[]) => {
    list.sort(
      (a, b) =>
        categoryLabel(a).localeCompare(categoryLabel(b)) ||
        a.id.localeCompare(b.id),
    );
    for (const node of list) sort(node.children);
  };
  sort(roots);
  return roots;
}
export function categoryError(
  error: unknown,
  operation:
    "read" | "create" | "content" | "move" | "delete" | "assign" = "read",
) {
  const status = getApiErrorStatus(error);
  if (status === 403)
    return "Недостаточно прав для выполнения операции с категориями.";
  if (status === 404) return "Категория или товар не найдены. Обновите данные.";
  if (status === 409)
    return operation === "delete"
      ? "Категория содержит подкатегории или связана с товарами."
      : operation === "move"
        ? "Нельзя переместить категорию в себя или в её потомка. Обновите дерево."
        : "Конфликт данных при создании категории.";
  if (status === 422)
    return operation === "assign"
      ? "Выберите основную категорию из назначенных товару."
      : "Проверьте название, язык и выбранную категорию.";
  return getApiErrorMessage(
    error,
    "Не удалось выполнить запрос. Попробуйте ещё раз.",
  );
}
