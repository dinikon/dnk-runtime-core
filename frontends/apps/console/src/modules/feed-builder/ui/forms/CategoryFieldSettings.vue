<script setup lang="ts">
import { computed, ref } from "vue";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { CatalogCategory } from "@/modules/catalog";
import { cloneSchemaValue } from "../../model/feed-schema.clone";
import { newCategory } from "../../model/feed-categories.draft";
import type { CategoryFallback, CategoryPropertyDefinition, CategoryPropertyPlacement, CategoryPropertyType, CategoryType, FeedCategoryNode, FeedCategoryRule } from "../../model/feed-categories.types";
import type { CalculationMetadata } from "../../model/feed-calculation.types";
import type { SchemaFieldDraft, SchemaMetadata } from "../../model/feed-schema.types";
import CalculationNodeEditor from "./CalculationNodeEditor.vue";
import CategoryObjectEditor from "./CategoryObjectEditor.vue";

const props = defineProps<{
  value: CategoryType;
  exportSettings: SchemaFieldDraft["export"];
  savedIds: string[];
  locales: SchemaMetadata["locales"];
  catalog: CatalogCategory[];
  catalogLoading: boolean;
  catalogError: boolean;
  calculationMetadata?: CalculationMetadata;
  disabled: boolean;
}>();
const emit = defineEmits<{ change: [value: CategoryType, settings: SchemaFieldDraft["export"]]; retryCatalog: [] }>();
const selected = ref("");
const catalogId = ref("");
const includeBranch = ref(false);
const selectedRule = ref("");
const ruleCatalogId = ref("");
const error = ref("");
const propertyKey = ref("");
const propertyKind = ref<CategoryPropertyType>("string");
const selectClass = "w-full rounded-md border bg-background px-2 py-2 text-sm";
const node = computed(() => props.value.value.nodes.find((item) => item.id === selected.value));
const rule = computed(() => props.value.value.rules.find((item) => item.id === selectedRule.value));
const catalogById = computed(() => new Map(props.catalog.map((item) => [item.id, item])));
const linkedByCatalogId = computed(() => new Map(props.value.value.nodes.flatMap((item) => item.catalogId ? [[item.catalogId, item] as const] : [])));
const nodesById = computed(() => new Map(props.value.value.nodes.map((item) => [item.id, item])));
const linked = computed(() => props.value.value.nodes.filter((item) => item.catalogId !== null) ?? []);

function input(event: Event): string {
  return (event.target as HTMLInputElement | HTMLSelectElement).value;
}
function update(apply: (draft: CategoryType, settings: SchemaFieldDraft["export"]) => void): void {
  if (props.disabled) return;
  const draft = cloneSchemaValue(props.value);
  const settings = cloneSchemaValue(props.exportSettings);
  apply(draft, settings);
  emit("change", draft, settings);
}
function changeNode(change: Partial<FeedCategoryNode>): void {
  update((draft) => {
    const item = draft.value.nodes.find((entry) => entry.id === selected.value);
    if (item) Object.assign(item, change);
  });
}
function addProperty(): void {
  const key = propertyKey.value.trim();
  if (!/^[A-Za-z_][A-Za-z0-9_.-]{0,127}$/.test(key) || props.value.objectSchema.fields.some(field => field.key === key)) {
    error.value = "Введите уникальный ключ свойства из латинских букв, цифр и знаков _ . -.";
    return;
  }
  update(draft => { draft.objectSchema.fields.push({
    key, kind: propertyKind.value, required: false, xml: { name: key, placement: "ELEMENT" }, source: null,
  }); });
  propertyKey.value = "";
  error.value = "";
}
function updateProperty(key: string, change: Partial<CategoryPropertyDefinition>): void {
  update(draft => {
    const field = draft.objectSchema.fields.find(item => item.key === key);
    if (field) Object.assign(field, change);
  });
}
function removeProperty(key: string): void {
  if (props.value.value.nodes.some(item => Object.hasOwn(item.values, key))) {
    error.value = "Очистите значения свойства в записях перед удалением.";
    return;
  }
  update(draft => { draft.objectSchema.fields = draft.objectSchema.fields.filter(item => item.key !== key); });
  error.value = "";
}
function toggleDocument(enabled: boolean): void {
  update((_draft, settings) => {
    if (enabled) settings.document = { container: "categories", item: "category", parent: "ROOT", layout: "FLAT", parentAttribute: "parentId" };
    else delete settings.document;
  });
}
function togglePublication(enabled: boolean): void {
  update((draft, settings) => {
    if (enabled) settings.publication = { valueKey: draft.objectSchema.idKey, required: false };
    else delete settings.publication;
  });
}
function changeRule(change: Partial<FeedCategoryRule>): void {
  update((draft) => {
    const item = draft.value.rules.find((entry) => entry.id === selectedRule.value);
    if (item) Object.assign(item, change);
  });
}
function effectiveParent(item: FeedCategoryNode): string | null {
  const sourceParent = item.catalogId ? catalogById.value.get(item.catalogId)?.parentId : null;
  return item.inheritParent && sourceParent ? linkedByCatalogId.value.get(sourceParent)?.id ?? null : item.parentId;
}
function nodeName(item: FeedCategoryNode): string {
  const source = item.catalogId ? catalogById.value.get(item.catalogId) : undefined;
  return String(item.values[props.value.objectSchema.labelKey] || source?.name || source?.fallbackName || "Категория без названия");
}
function nodePath(item: FeedCategoryNode): string {
  const names = [nodeName(item)];
  const visited = new Set([item.id]);
  let parent = effectiveParent(item);
  while (parent && !visited.has(parent)) {
    visited.add(parent);
    const ancestor = nodesById.value.get(parent);
    if (!ancestor) break;
    names.unshift(nodeName(ancestor));
    parent = effectiveParent(ancestor);
  }
  return names.join(" / ");
}
const orderedNodes = computed(() =>
  [...(props.value.value.nodes ?? [])].sort((left, right) =>
    nodePath(left).localeCompare(nodePath(right), props.value.locale),
  ),
);
function catalogPath(item: CatalogCategory): string {
  const names = [item.name ?? item.fallbackName];
  const visited = new Set([item.id]);
  let parent = item.parentId;
  while (parent && !visited.has(parent)) {
    visited.add(parent);
    const ancestor = catalogById.value.get(parent);
    if (!ancestor) break;
    names.unshift(ancestor.name ?? ancestor.fallbackName);
    parent = ancestor.parentId;
  }
  return names.join(" / ");
}
function addOwn(): void {
  const item = { ...newCategory(), parentId: selected.value || null };
  update((draft) => { draft.value.nodes.push(item); });
  selected.value = item.id;
  error.value = "";
}
function connect(): void {
  if (!catalogId.value || !catalogById.value.has(catalogId.value)) return;
  const root = catalogId.value;
  const wanted = new Set<string>([root]);
  if (includeBranch.value) {
    const children = new Map<string, string[]>();
    for (const item of props.catalog) {
      if (item.parentId) children.set(item.parentId, [...(children.get(item.parentId) ?? []), item.id]);
    }
    const queue = [root];
    for (const id of queue)
      for (const child of children.get(id) ?? [])
        if (!wanted.has(child)) { wanted.add(child); queue.push(child); }
  }
  let parent = catalogById.value.get(root)?.parentId;
  while (parent && !wanted.has(parent)) {
    wanted.add(parent);
    parent = catalogById.value.get(parent)?.parentId;
  }
  if ((props.value.value.nodes.length ?? 0) + [...wanted].filter((id) => !linkedByCatalogId.value.has(id)).length > 1000) {
    error.value = "В фиде допустимо до 1000 категорий.";
    return;
  }
  update((draft) => {
    for (const id of wanted) {
      if (linkedByCatalogId.value.has(id)) continue;
      const item = { ...newCategory(), catalogId: id, inheritParent: true };
      draft.value.nodes.push(item);
      if (id === root) selected.value = item.id;
    }
    const existing = linkedByCatalogId.value.get(root);
    if (existing) selected.value = existing.id;
  });
  error.value = "";
}
function removeNode(): void {
  const current = node.value;
  if (!current) return;
  const hasChildren = props.value.value.nodes.some((item) => effectiveParent(item) === current.id
    || (item.inheritParent && catalogById.value.get(item.catalogId ?? "")?.parentId === current.catalogId && current.catalogId !== null));
  if (hasChildren || props.value.value.rules.some((item) => item.targetId === current.id) || props.value.value.fallbackId === current.id) {
    error.value = "Перенесите дочерние категории и измените правила, которые используют этот узел.";
    return;
  }
  update((draft) => {
    draft.value.nodes = draft.value.nodes.filter((item) => item.id !== current.id);
    draft.value.catalogPriority = draft.value.catalogPriority.filter((id) => id !== current.id);
  });
  selected.value = "";
  error.value = "";
}
function trimNames(enabled: boolean): void {
  update((draft) => {
    draft.nameTransforms = draft.nameTransforms.filter((item) => item.operation !== "string.trim");
    if (enabled) draft.nameTransforms.unshift({ operation: "string.trim", parameters: {} });
  });
}
function truncateNames(raw: string): void {
  if (raw && (!/^\d+$/.test(raw) || Number(raw) < 1 || Number(raw) > 255)) {
    error.value = "Укажите длину от 1 до 255 символов.";
    return;
  }
  update((draft) => {
    draft.nameTransforms = draft.nameTransforms.filter((item) => item.operation !== "string.truncate");
    if (raw) draft.nameTransforms.push({ operation: "string.truncate", parameters: { maxLength: Number(raw) } });
  });
  error.value = "";
}
const nameLimit = computed(() => props.value.nameTransforms.find(item => item.operation === "string.truncate")?.parameters.maxLength);
function setFallback(fallback: CategoryFallback): void {
  update((draft) => {
    draft.value.fallback = fallback;
    draft.value.fallbackId = fallback === "FIXED" ? draft.value.nodes[0]?.id ?? null : null;
  });
}
function setPriority(id: string, enabled: boolean): void {
  update((draft) => {
    draft.value.catalogPriority = enabled
      ? [...draft.value.catalogPriority, id]
      : draft.value.catalogPriority.filter((item) => item !== id);
  });
}
function move<T>(items: T[], index: number, offset: number): void {
  const other = index + offset;
  if (index < 0 || other < 0 || other >= items.length) return;
  [items[index], items[other]] = [items[other]!, items[index]!];
}
function addRule(): void {
  const target = selected.value || props.value.value.nodes[0]?.id;
  if (!target) return;
  const id = crypto.randomUUID();
  update((draft) => {
    draft.value.rules.push({
      id, targetId: target, includeDescendants: false, label: `Правило ${draft.value.rules.length + 1}`,
      condition: ruleCatalogId.value
        ? { kind: "comparison", operator: "CONTAINS",
            left: { kind: "parameter", parameter: "product.category_ids" },
            right: { kind: "scalar", valueType: "uuid", value: ruleCatalogId.value } }
        : { kind: "presence", operator: "EXISTS", parameter: "stock.quantity" },
    });
  });
  selectedRule.value = id;
}
</script>

<template>
  <section class="grid min-w-0 gap-4 rounded-lg border p-4" aria-labelledby="category-field-heading">
    <h3 id="category-field-heading" class="font-semibold">Поле категории</h3>
    <fieldset class="grid min-w-0 gap-4" :disabled="disabled">
      <section class="grid gap-3" aria-label="Структура объекта">
        <h4 class="text-sm font-semibold">Структура объекта</h4>
        <div class="grid gap-2 sm:grid-cols-[minmax(0,1fr)_auto_auto]">
          <Input v-model="propertyKey" aria-label="Ключ нового свойства" placeholder="Например, prom_id" />
          <select v-model="propertyKind" :class="selectClass" aria-label="Тип нового свойства">
            <option value="string">Короткий текст</option><option value="text">Длинный текст</option>
            <option value="integer">Целое число</option><option value="boolean">Логическое</option>
          </select>
          <Button type="button" variant="outline" :disabled="!propertyKey.trim() || value.objectSchema.fields.length >= 64" @click="addProperty">Добавить свойство</Button>
        </div>
        <div v-for="property in value.objectSchema.fields" :key="property.key" class="grid min-w-0 gap-2 rounded-md border p-3">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <span class="break-all text-sm font-medium">{{ property.key }}</span>
            <label class="flex items-center gap-2 text-sm">
              <input type="checkbox" :checked="property.required" :disabled="property.key === value.objectSchema.idKey"
                @change="updateProperty(property.key, { required: ($event.target as HTMLInputElement).checked })" />
              Обязательное
            </label>
            <Button type="button" variant="ghost" size="sm"
              :disabled="[value.objectSchema.idKey, value.objectSchema.labelKey, exportSettings.publication?.valueKey].includes(property.key)"
              :aria-label="`Удалить свойство ${property.key}`" @click="removeProperty(property.key)">Удалить</Button>
          </div>
          <div class="grid min-w-0 gap-2 sm:grid-cols-2">
            <select :class="selectClass" :aria-label="`Вывод ${property.key}`" :value="property.xml.placement"
              @change="updateProperty(property.key, { xml: { ...property.xml, placement: input($event) as CategoryPropertyPlacement } })">
              <option value="ATTRIBUTE">Атрибут</option><option value="ELEMENT">Дочерний тег</option>
              <option value="TEXT">Текст элемента</option><option value="NONE">Только данные</option>
            </select>
            <Input v-if="property.xml.placement === 'ATTRIBUTE' || property.xml.placement === 'ELEMENT'"
              :aria-label="`Имя XML для ${property.key}`" :model-value="property.xml.name"
              @update:model-value="updateProperty(property.key, { xml: { ...property.xml, name: String($event) } })" />
          </div>
        </div>
        <div class="grid gap-2 sm:grid-cols-2">
          <label class="grid gap-1 text-sm">Свойство ID
            <select :class="selectClass" aria-label="Свойство ID" :value="value.objectSchema.idKey" :disabled="savedIds.length > 0"
              @change="update(draft => { draft.objectSchema.idKey = input($event); })">
              <option v-for="property in value.objectSchema.fields.filter(item => !item.source && ['string', 'integer'].includes(item.kind))"
                :key="property.key" :value="property.key">{{ property.key }}</option>
            </select>
          </label>
          <label class="grid gap-1 text-sm">Свойство названия
            <select :class="selectClass" aria-label="Свойство названия" :value="value.objectSchema.labelKey"
              @change="update(draft => { draft.objectSchema.labelKey = input($event); })">
              <option v-for="property in value.objectSchema.fields.filter(item => item.kind === 'text' || item.kind === 'string')"
                :key="property.key" :value="property.key">{{ property.key }}</option>
            </select>
          </label>
        </div>
      </section>
      <section class="grid gap-3 border-t pt-4" aria-label="Вывод категории">
        <h4 class="text-sm font-semibold">Вывод категории</h4>
        <label class="flex items-center gap-2 text-sm">
          <input type="checkbox" :checked="!!exportSettings.document"
            @change="toggleDocument(($event.target as HTMLInputElement).checked)" /> Вывести объекты в документ
        </label>
        <div v-if="exportSettings.document" class="grid gap-2 sm:grid-cols-2">
          <label class="grid gap-1 text-sm">Имя контейнера
            <Input aria-label="Имя контейнера" :model-value="exportSettings.document.container"
              @update:model-value="update((_draft, settings) => { settings.document!.container = String($event); })" />
          </label>
          <label class="grid gap-1 text-sm">Имя записи
            <Input aria-label="Имя записи" :model-value="exportSettings.document.item"
              @update:model-value="update((_draft, settings) => { settings.document!.item = String($event); })" />
          </label>
          <label class="grid gap-1 text-sm">Куда вывести дерево
            <select :class="selectClass" aria-label="Куда вывести дерево" :value="exportSettings.document.parent"
              @change="update((_draft, settings) => { settings.document!.parent = input($event) as 'ROOT' | 'SHOP'; })">
              <option value="ROOT">В корень</option><option value="SHOP">В shop (YML)</option>
            </select>
          </label>
          <label class="grid gap-1 text-sm">Вложенность в XML
            <select :class="selectClass" aria-label="Вложенность в XML" :value="exportSettings.document.layout"
              @change="update((_draft, settings) => { settings.document!.layout = input($event) as 'FLAT' | 'NESTED'; })">
              <option value="FLAT">Ссылка на родителя</option><option value="NESTED">Вложенные элементы</option>
            </select>
          </label>
          <label v-if="exportSettings.document.layout === 'FLAT'" class="grid gap-1 text-sm">Атрибут родителя
            <Input :model-value="exportSettings.document.parentAttribute"
              @update:model-value="update((_draft, settings) => { settings.document!.parentAttribute = String($event); })" />
          </label>
        </div>
        <label class="flex items-center gap-2 text-sm">
          <input type="checkbox" :checked="!!exportSettings.publication"
            @change="togglePublication(($event.target as HTMLInputElement).checked)" /> Вывести ссылку в предложение
        </label>
        <div v-if="exportSettings.publication" class="grid gap-2 sm:grid-cols-2">
          <label class="grid gap-1 text-sm">Свойство для ссылки
            <select :class="selectClass" aria-label="Свойство для ссылки" :value="exportSettings.publication.valueKey"
              @change="update((_draft, settings) => { settings.publication!.valueKey = input($event); })">
              <option v-for="property in value.objectSchema.fields" :key="property.key" :value="property.key">{{ property.key }}</option>
            </select>
          </label>
          <label class="flex items-center gap-2 text-sm">
            <input type="checkbox" :checked="exportSettings.publication.required"
              @change="update((_draft, settings) => { settings.publication!.required = ($event.target as HTMLInputElement).checked; })" />
            Ссылка обязательна
          </label>
        </div>
      </section>
      <div class="grid gap-3 border-t pt-4">
        <label class="grid gap-1 text-sm">Язык категорий Catalog
          <select :class="selectClass" :value="value.locale" @change="update(draft => { draft.locale = input($event); })">
            <option v-for="locale in locales" :key="locale.code" :value="locale.code">{{ locale.name }}</option>
          </select>
        </label>
      </div>
      <div class="grid items-center gap-3 sm:grid-cols-2">
        <label class="flex items-center gap-2 text-sm">
          <input type="checkbox" :checked="value.nameTransforms.some(item => item.operation === 'string.trim')"
            @change="trimNames(($event.target as HTMLInputElement).checked)" />
          Убирать пробелы по краям названий
        </label>
        <label class="grid gap-1 text-sm">Максимальная длина названий в XML
          <Input :model-value="nameLimit ?? ''" inputmode="numeric" placeholder="Без обрезки"
            @update:model-value="truncateNames(String($event))" />
        </label>
      </div>
      <div class="grid min-w-0 gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.35fr)]">
        <div class="grid min-w-0 content-start gap-3">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <h3 class="text-sm font-semibold">Дерево фида</h3>
            <Button type="button" variant="outline" size="sm" :disabled="value.value.nodes.length >= 1000" @click="addOwn">Создать категорию</Button>
          </div>
          <p v-if="!value.value.nodes.length" class="text-sm text-muted-foreground">Добавьте свою категорию или подключите ветку Catalog.</p>
          <ul v-else class="grid max-h-64 gap-1 overflow-auto">
            <li v-for="item in orderedNodes" :key="item.id">
              <button type="button" :aria-pressed="selected === item.id"
                class="w-full break-words rounded-md border px-3 py-2 text-left text-sm aria-pressed:bg-muted"
                @click="selected = item.id; error = ''">
                {{ nodePath(item) }}<span v-if="item.values[value.objectSchema.idKey] !== undefined" class="ml-2 text-muted-foreground">#{{ item.values[value.objectSchema.idKey] }}</span>
              </button>
            </li>
          </ul>
          <label class="grid gap-1 text-sm">Категория из Catalog
            <select v-model="catalogId" aria-label="Категория из Catalog" :class="selectClass" :disabled="catalogLoading || catalogError">
              <option value="">Выберите категорию</option>
              <option v-for="item in catalog" :key="item.id" :value="item.id">{{ catalogPath(item) }}</option>
            </select>
          </label>
          <label class="flex gap-2 text-sm"><input v-model="includeBranch" type="checkbox" /> Включить потомков</label>
          <div class="flex flex-wrap gap-2">
            <Button type="button" variant="outline" size="sm" :disabled="!catalogId || catalogLoading || catalogError" @click="connect">Подключить / обновить ветку</Button>
            <Button type="button" variant="ghost" size="sm" :disabled="catalogLoading" @click="emit('retryCatalog')">Обновить Catalog</Button>
          </div>
          <p v-if="catalogError" role="alert" class="text-sm text-destructive">Дерево Catalog недоступно.</p>
        </div>
        <div v-if="node" :key="node.id" class="grid min-w-0 content-start gap-3 rounded-md border p-3">
          <div class="flex items-center justify-between gap-2">
            <h3 class="text-sm font-semibold">{{ node.catalogId ? "Связана с Catalog" : "Собственная категория" }}</h3>
            <Button type="button" variant="ghost" size="sm" @click="removeNode">Удалить категорию</Button>
          </div>
          <CategoryObjectEditor
            :fields="value.objectSchema.fields" :values="node.values" :id-key="value.objectSchema.idKey"
            :saved="savedIds.includes(node.id)" :catalog-linked="!!node.catalogId" :disabled="disabled"
            @change="changeNode({ values: $event })"
          />
          <label class="grid gap-1 text-sm">Родитель категории
            <select :class="selectClass" :value="node.inheritParent ? 'inherit' : (node.parentId ?? '')"
              @change="changeNode({ inheritParent: input($event) === 'inherit', parentId: input($event) === 'inherit' ? null : input($event) || null })">
              <option v-if="node.catalogId" value="inherit">Как в Catalog</option>
              <option value="">Верхний уровень</option>
              <option v-for="item in value.value.nodes.filter(entry => entry.id !== node?.id)" :key="item.id" :value="item.id">{{ nodePath(item) }}</option>
            </select>
          </label>
        </div>
      </div>
      <p v-if="error" role="alert" class="text-sm text-destructive">{{ error }}</p>
      <div class="grid min-w-0 gap-3 border-t pt-4">
        <h3 class="text-sm font-semibold">Правила назначения</h3>
        <div class="flex flex-wrap items-end gap-2">
          <label class="grid min-w-48 flex-1 gap-1 text-sm">Условие по категории Catalog
            <select v-model="ruleCatalogId" aria-label="Условие по категории Catalog" :class="selectClass">
              <option value="">Настроить условие вручную</option>
              <option v-for="item in catalog" :key="item.id" :value="item.id">{{ catalogPath(item) }}</option>
            </select>
          </label>
          <Button type="button" variant="outline" size="sm" :disabled="!value.value.nodes.length || value.value.rules.length >= 100 || !calculationMetadata" @click="addRule">Добавить правило</Button>
        </div>
        <div v-for="(item, index) in value.value.rules" :key="item.id" class="flex flex-wrap items-center gap-2">
          <Button type="button" variant="outline" size="sm" :aria-pressed="item.id === selectedRule" @click="selectedRule = item.id">{{ item.label }}</Button>
          <Button type="button" variant="ghost" size="sm" :disabled="index === 0" :aria-label="`Поднять правило ${item.label}`" @click="update(draft => move(draft.value.rules, index, -1))">↑</Button>
          <Button type="button" variant="ghost" size="sm" :disabled="index === value.value.rules.length - 1" :aria-label="`Опустить правило ${item.label}`" @click="update(draft => move(draft.value.rules, index, 1))">↓</Button>
          <Button type="button" variant="ghost" size="sm" @click="update(draft => { draft.value.rules.splice(index, 1); })">Удалить правило</Button>
        </div>
        <div v-if="rule && calculationMetadata" class="grid min-w-0 gap-3 rounded-md border p-3">
          <label class="grid gap-1 text-sm">Название правила
            <Input :model-value="rule.label" @update:model-value="changeRule({ label: String($event) })" />
          </label>
          <label class="flex items-center gap-2 text-sm">
            <input type="checkbox" :checked="rule.includeDescendants"
              @change="changeRule({ includeDescendants: ($event.target as HTMLInputElement).checked })" />
            Учитывать дочерние категории Catalog в условии
          </label>
          <CalculationNodeEditor :node="rule.condition" :metadata="calculationMetadata" :issues="[]"
            category="condition" :path="['condition']" :disabled="disabled"
            @change="changeRule({ condition: $event })" />
          <label class="grid gap-1 text-sm">Назначить категорию
            <select :class="selectClass" :value="rule.targetId" @change="changeRule({ targetId: input($event) })">
              <option v-for="item in value.value.nodes" :key="item.id" :value="item.id">{{ nodePath(item) }}</option>
            </select>
          </label>
        </div>
        <label class="grid gap-1 text-sm">Если ни одно правило не подошло
          <select aria-label="Если ни одно правило не подошло" :class="selectClass" :value="value.value.fallback" @change="setFallback(input($event) as CategoryFallback)">
            <option value="CATALOG">Наследовать из Catalog</option>
            <option value="FIXED" :disabled="!value.value.nodes.length">Выбрать категорию</option>
            <option value="NONE">Без категории</option>
          </select>
        </label>
        <label v-if="value.value.fallback === 'FIXED'" class="grid gap-1 text-sm">Категория по умолчанию
          <select aria-label="Категория по умолчанию" :class="selectClass" :value="value.value.fallbackId" @change="update(draft => { draft.value.fallbackId = input($event); })">
            <option v-for="item in value.value.nodes" :key="item.id" :value="item.id">{{ nodePath(item) }}</option>
          </select>
        </label>
        <div v-if="value.value.fallback === 'CATALOG' && linked.length > 1" class="grid gap-2">
          <p class="text-sm">Приоритет при нескольких категориях Catalog</p>
          <div v-for="item in linked" :key="item.id" class="flex flex-wrap items-center gap-2 text-sm">
            <label class="flex items-center gap-2">
              <input type="checkbox" :checked="value.value.catalogPriority.includes(item.id)" @change="setPriority(item.id, ($event.target as HTMLInputElement).checked)" />
              {{ nodePath(item) }}
            </label>
            <template v-if="value.value.catalogPriority.includes(item.id)">
              <span>{{ value.value.catalogPriority.indexOf(item.id) + 1 }}</span>
              <Button type="button" variant="ghost" size="sm" :disabled="value.value.catalogPriority.indexOf(item.id) === 0"
                :aria-label="`Поднять приоритет ${nodeName(item)}`"
                @click="update(draft => move(draft.value.catalogPriority, draft.value.catalogPriority.indexOf(item.id), -1))">↑</Button>
            </template>
          </div>
        </div>
      </div>
    </fieldset>
  </section>
</template>
