<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { Button } from "@/components/ui/button";
import type {
  CatalogAttribute,
  Product,
  ProductKind,
  ProductStructureDraft,
} from "../../model/catalog.types";
const props = defineProps<{
  initial: Product | null;
  attributes: CatalogAttribute[];
  targetKind: ProductKind;
  transition?: boolean;
  pending: boolean;
  disabled: boolean;
  reset: number;
}>();
const emit = defineEmits<{
  submit: [value: ProductStructureDraft];
  dirty: [value: boolean];
}>();
type Row = {
  key: string;
  id: string | null;
  virtual: boolean;
  selection: Record<string, string>;
};
const kind = ref<ProductKind>(props.targetKind),
  axes = ref<{ attributeId: string; optionIds: string[] }[]>([]),
  rows = ref<Row[]>([]),
  defaultKey = ref(""),
  simpleKey = ref(""),
  errors = ref<string[]>([]),
  dirty = ref(false);
function newRow(): Row {
  return { key: crypto.randomUUID(), id: null, virtual: false, selection: {} };
}
function mark() {
  dirty.value = true;
  emit("dirty", true);
}
function same(a: Record<string, string>, b: Record<string, string>) {
  return (
    Object.keys(a).length === Object.keys(b).length &&
    Object.keys(a).every((k) => a[k] === b[k])
  );
}
function resetFields() {
  kind.value = props.targetKind;
  axes.value = (props.initial?.axes ?? []).map((a) => ({
    attributeId: a.attributeId,
    optionIds: [...a.optionIds],
  }));
  rows.value = props.initial?.variants.map((v) => ({
    key: v.id,
    id: v.id,
    virtual: v.virtual,
    selection: { ...v.selection },
  })) ?? [newRow(), newRow()];
  simpleKey.value = rows.value[0]?.key ?? "";
  const selected = props.initial?.defaultSelection;
  defaultKey.value = selected
    ? (rows.value.find((v) => same(v.selection, selected))?.key ?? "")
    : "";
  errors.value = [];
  dirty.value = false;
  emit("dirty", false);
}
resetFields();
watch(() => props.reset, resetFields);
watch(
  () => props.initial,
  () => {
    if (!dirty.value) resetFields();
  },
);
watch(() => props.targetKind, resetFields);
function definition(id: string) {
  return props.attributes.find((a) => a.id === id);
}
function changeAxis(index: number, id: string) {
  const axis = axes.value[index];
  if (!axis) return;
  const old = axis.attributeId;
  for (const row of rows.value) delete row.selection[old];
  axis.attributeId = id;
  axis.optionIds = definition(id)?.options.map((o) => o.id) ?? [];
  for (const row of rows.value) row.selection[id] = axis.optionIds[0] ?? "";
  mark();
}
function addAxis() {
  const attribute = props.attributes.find(
    (a) => !axes.value.some((x) => x.attributeId === a.id) && a.options.length,
  );
  if (!attribute) {
    errors.value = ["Создайте enum-характеристику с разрешёнными значениями."];
    return;
  }
  axes.value.push({
    attributeId: attribute.id,
    optionIds: attribute.options.map((o) => o.id),
  });
  for (const row of rows.value)
    row.selection[attribute.id] = attribute.options[0]?.id ?? "";
  mark();
}
function removeAxis(index: number) {
  const [axis] = axes.value.splice(index, 1);
  if (axis)
    for (const row of rows.value) delete row.selection[axis.attributeId];
  mark();
}
function addVariant() {
  const row = newRow();
  for (const axis of axes.value)
    row.selection[axis.attributeId] = axis.optionIds[0] ?? "";
  rows.value.push(row);
  mark();
}
function removeVariant(key: string) {
  rows.value = rows.value.filter((r) => r.key !== key);
  if (defaultKey.value === key) defaultKey.value = "";
  if (simpleKey.value === key) simpleKey.value = rows.value[0]?.key ?? "";
  mark();
}
const removed = computed(() => {
  const retained = new Set(
    kind.value === "simple"
      ? [rows.value.find((r) => r.key === simpleKey.value)?.id]
      : rows.value.map((r) => r.id),
  );
  return props.initial?.variants.filter((v) => !retained.has(v.id)) ?? [];
});
function submit() {
  errors.value = [];
  if (kind.value === "simple") {
    const row = rows.value.find((r) => r.key === simpleKey.value);
    if (!row) {
      errors.value = ["Выберите оставляемую позицию."];
      return;
    }
    emit("submit", {
      kind: "simple",
      variant: { id: row.id, virtual: row.virtual, selection: {} },
    });
    return;
  }
  if (!axes.value.length) errors.value.push("Добавьте хотя бы одну ось.");
  if (rows.value.length < 2)
    errors.value.push(
      "VARIABLE требует минимум две позиции. Для одной используйте смену вида.",
    );
  if (new Set(axes.value.map((a) => a.attributeId)).size !== axes.value.length)
    errors.value.push("Характеристики осей не должны повторяться.");
  const combinations = new Set<string>();
  for (const row of rows.value) {
    if (
      axes.value.some(
        (a) =>
          !a.optionIds.length ||
          !a.optionIds.includes(row.selection[a.attributeId] ?? ""),
      )
    )
      errors.value.push(
        "У каждой позиции выберите допустимое значение всех осей.",
      );
    const combination = JSON.stringify(
      axes.value
        .map((a) => [a.attributeId, row.selection[a.attributeId]])
        .sort(),
    );
    if (combinations.has(combination))
      errors.value.push("Комбинации позиций повторяются.");
    combinations.add(combination);
  }
  if (errors.value.length) return;
  const selected = rows.value.find((r) => r.key === defaultKey.value);
  emit("submit", {
    kind: "variable",
    axes: axes.value.map((a, position) => ({
      ...a,
      optionIds: [...a.optionIds],
      position,
    })),
    defaultSelection: selected ? { ...selected.selection } : null,
    variants: rows.value.map((r) => ({
      id: r.id,
      virtual: r.virtual,
      selection: Object.fromEntries(
        axes.value.map((a) => [
          a.attributeId,
          r.selection[a.attributeId] ?? "",
        ]),
      ),
    })),
  });
}
</script>
<template>
  <form class="space-y-5" @submit.prevent="submit">
    <fieldset :disabled="pending || disabled" class="min-w-0 space-y-5">
      <label v-if="transition" class="block space-y-2"
        ><span>Целевой вид</span
        ><select
          v-model="kind"
          aria-label="Целевой вид"
          class="w-full rounded-md border bg-background p-2"
          @change="mark"
        >
          <option :value="initial?.kind === 'simple' ? 'variable' : 'simple'">
            {{ initial?.kind === "simple" ? "VARIABLE" : "SIMPLE" }}
          </option>
        </select></label
      >
      <template v-if="kind === 'variable'">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <h2 class="font-medium">Оси вариаций</h2>
          <Button type="button" variant="outline" @click="addAxis"
            >Добавить ось</Button
          >
        </div>
        <p v-if="!attributes.length" class="text-sm text-muted-foreground">
          Сначала создайте enum-характеристики и их значения в справочнике
          Catalog.
        </p>
        <div
          v-for="(axis, index) in axes"
          :key="index"
          class="space-y-3 rounded-md border p-3"
        >
          <div class="flex flex-wrap gap-2">
            <select
              :value="axis.attributeId"
              :aria-label="`Характеристика оси ${index + 1}`"
              class="min-w-0 flex-1 rounded-md border bg-background p-2"
              @change="
                changeAxis(index, ($event.target as HTMLSelectElement).value)
              "
            >
              <option
                v-for="attribute in attributes"
                :key="attribute.id"
                :value="attribute.id"
              >
                {{ attribute.label ?? attribute.code }}
              </option></select
            ><Button type="button" variant="ghost" @click="removeAxis(index)"
              >Удалить ось</Button
            >
          </div>
          <div class="flex flex-wrap gap-3">
            <label
              v-for="option in definition(axis.attributeId)?.options ?? []"
              :key="option.id"
              class="flex items-center gap-2 text-sm"
              ><input
                v-model="axis.optionIds"
                type="checkbox"
                :value="option.id"
                @change="mark"
              />{{ option.label ?? option.code }}</label
            >
          </div>
        </div>
        <div class="flex flex-wrap items-center justify-between gap-2">
          <h2 class="font-medium">Позиции ({{ rows.length }})</h2>
          <Button type="button" variant="outline" @click="addVariant"
            >Добавить позицию</Button
          >
        </div>
        <div
          v-for="(row, index) in rows"
          :key="row.key"
          class="space-y-3 rounded-md border p-3"
        >
          <div class="flex flex-wrap items-center justify-between gap-2">
            <span class="text-sm font-medium"
              >Позиция {{ index + 1 }} ·
              {{ row.id ? "Существующая" : "Новая" }}</span
            ><Button
              type="button"
              variant="ghost"
              @click="removeVariant(row.key)"
              >Убрать позицию</Button
            >
          </div>
          <div class="grid gap-3 sm:grid-cols-2">
            <label
              v-for="axis in axes"
              :key="axis.attributeId"
              class="block space-y-1 text-sm"
              ><span>{{
                definition(axis.attributeId)?.label ??
                definition(axis.attributeId)?.code
              }}</span
              ><select
                v-model="row.selection[axis.attributeId]"
                :aria-label="`Позиция ${index + 1}: ${definition(axis.attributeId)?.label ?? definition(axis.attributeId)?.code}`"
                class="w-full rounded-md border bg-background p-2"
                @change="mark"
              >
                <option value="">Выберите значение</option>
                <option
                  v-for="option in definition(axis.attributeId)?.options.filter(
                    (o) => axis.optionIds.includes(o.id),
                  ) ?? []"
                  :key="option.id"
                  :value="option.id"
                >
                  {{ option.label ?? option.code }}
                </option>
              </select></label
            >
          </div>
          <label class="flex items-center gap-2 text-sm"
            ><input
              v-model="row.virtual"
              type="checkbox"
              @change="mark"
            />Виртуальная позиция</label
          >
        </div>
        <label class="block space-y-2"
          ><span>Выбор по умолчанию</span
          ><select
            v-model="defaultKey"
            aria-label="Выбор по умолчанию"
            class="w-full rounded-md border bg-background p-2"
            @change="mark"
          >
            <option value="">Не задан</option>
            <option
              v-for="(row, index) in rows"
              :key="row.key"
              :value="row.key"
            >
              Позиция {{ index + 1 }}
            </option>
          </select></label
        >
      </template>
      <template v-else>
        <label class="block space-y-2"
          ><span>Оставляемая позиция</span
          ><select
            v-model="simpleKey"
            aria-label="Оставляемая позиция"
            class="w-full rounded-md border bg-background p-2"
            @change="mark"
          >
            <option
              v-for="(row, index) in rows"
              :key="row.key"
              :value="row.key"
            >
              Позиция {{ index + 1 }} · {{ row.id }}
            </option>
          </select></label
        >
        <p class="text-sm text-muted-foreground">
          Оси удаляются. Контент товара сохраняется; переводы вариантов
          необходимо предварительно удалить отдельным действием.
        </p>
      </template>
      <div v-if="removed.length" class="rounded-md bg-muted p-3 text-sm">
        <p class="font-medium">Будут удалены позиции:</p>
        <p v-for="variant in removed" :key="variant.id" class="break-all">
          {{ variant.effectiveTitle ?? variant.id }} · Переводы:
          {{ variant.locales.join(", ") || "нет" }}
        </p>
        <p>Сервер отклонит удаление позиции с переводами.</p>
      </div>
      <ul
        v-if="errors.length"
        role="alert"
        class="list-inside list-disc text-sm text-destructive"
      >
        <li v-for="error in [...new Set(errors)]" :key="error">{{ error }}</li>
      </ul>
      <div class="flex flex-wrap gap-2">
        <Button type="submit">{{
          pending
            ? "Сохранение…"
            : transition
              ? "Сменить вид"
              : initial
                ? "Сохранить структуру"
                : "Создать VARIABLE"
        }}</Button
        ><Button type="button" variant="outline" @click="resetFields"
          >Отменить</Button
        >
      </div>
    </fieldset>
  </form>
</template>
