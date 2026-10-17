<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { getApiErrorMessage } from "@/app/providers/http";
import { useProductPage } from "../../model/use-product-page";
import {
  kindLabels,
  productTabs,
  selectionLabel,
  statusLabels,
  variantRow,
} from "../../model/product-presentation";
import type {
  ProductSection,
  ProductStructure,
} from "../../model/product.types";
import ProductHeader from "../product/ProductHeader.vue";
import ProductFieldsBlock from "../product/ProductFieldsBlock.vue";
import ProductVariantRow from "../product/ProductVariantRow.vue";
import ProductVariantEditor from "../product/ProductVariantEditor.vue";
import ProductEditorSidebar from "../product/ProductEditorSidebar.vue";
import CatalogItemStructureForm from "../forms/CatalogItemStructureForm.vue";
const {
  ctx,
  id,
  item,
  attributes,
  categories,
  tags,
  schema,
  variants,
  offset,
  variant,
  variantId,
  visited,
  allVariants,
  structure,
  structureRequested,
  tab,
  selectTab,
  selectVariant,
  draft,
  pending,
  error,
  conflict,
  blocked,
  isDirty,
  resetFor,
  mark,
  save,
  inherit,
  upload,
  reload,
  replaceStructure,
  imageUrl,
} = useProductPage(true);
watch(
  () => item.data.value,
  (v) => {
    if (v?.kind === "variant")
      void ctx.router.replace({
        path: `/catalog/items/${v.rootId}/edit`,
        query: { ...ctx.route.query, tab: "variants", variant: v.id },
      });
  },
  { immediate: true },
);
const schemaVersion = computed(
  () => schema.data.value?.schema.schema_version ?? 0,
);
const rootGroups = [
  { tab: "general", sections: ["price", "virtual"] },
  { tab: "inventory", sections: ["sku", "stock"] },
  { tab: "shipping", sections: ["measurements"] },
  { tab: "attributes", sections: ["attributes"] },
  { tab: "additional", sections: ["metadata"] },
] as const;
const tabs = computed(() =>
  productTabs.filter((t) =>
    item.data.value?.kind === "variable"
      ? t.id !== "general"
      : t.id !== "variants",
  ),
);
const rows = computed(
  () =>
    variants.data.value?.items.map((v) =>
      variantRow(v, attributes.data.value ?? [], imageUrl),
    ) ?? [],
);
function dirtyTab(value: string) {
  if (
    (value === "attributes" || value === "variants") &&
    isDirty(id.value, "structure")
  )
    return true;
  if (value === "variants")
    return Object.entries(draft.dirty).some(
      ([key, dirty]) => !key.startsWith(`${id.value}:`) && dirty,
    );
  return (
    rootGroups
      .find((g) => g.tab === value)
      ?.sections.some((s) => isDirty(id.value, s)) ?? false
  );
}
const sidebarSections: ProductSection[] = [
  "status",
  "galleries",
  "categories",
  "tags",
];
const variantSections: ProductSection[] = [
  "content",
  "status",
  "sku",
  "price",
  "virtual",
  "stock",
  "measurements",
  "attributes",
  "metadata",
  "galleries",
];
const dirtySections = (childId: string) =>
  variantSections.filter((s) => isDirty(childId, s));
const resets = (childId: string) =>
  Object.fromEntries(variantSections.map((s) => [s, resetFor(childId, s)]));
const transition = ref(false),
  selectedChild = ref("");
function openTransition() {
  structureRequested.value = true;
  transition.value = true;
}
async function toVariable(value: ProductStructure, carryIndex: number) {
  if (
    !window.confirm(
      "Коммерческие значения будут перенесены выбранному варианту. Продолжить?",
    )
  )
    return;
  await save(id.value, "kind", {
    kind: "variable",
    structure: value,
    carry_to_index: carryIndex,
  });
  if (!error.value) {
    mark(id.value, "kind", false);
    transition.value = false;
    selectTab("variants");
  }
}
async function toSimple() {
  if (
    !selectedChild.value ||
    !allVariants.data.value ||
    !window.confirm(
      "Выбранный вариант станет простым товаром. Все варианты и их собственные данные будут удалены. Продолжить?",
    )
  )
    return;
  await save(id.value, "kind", {
    kind: "simple",
    selected_item_id: selectedChild.value,
    discarded_ids: allVariants.data.value.map((v) => v.id),
  });
  if (!error.value) {
    transition.value = false;
    void ctx.router.replace({
      query: { ...ctx.route.query, tab: "general", variant: undefined },
    });
  }
}
const structureAttributes = computed(() =>
  (attributes.data.value ?? []).filter(
    (a) =>
      !item.data.value?.own.attributes.some((v) => v.attribute_id === a.id),
  ),
);
function closeTransition(value: boolean) {
  if (
    !value &&
    isDirty(id.value, "kind") &&
    !window.confirm("Отказаться от несохранённой структуры нового вида?")
  )
    return;
  transition.value = value;
  if (!value) mark(id.value, "kind", false);
}
</script>
<template>
  <div class="min-h-0 flex-1 overflow-y-auto">
    <div class="mx-auto flex w-full max-w-[1440px] flex-col gap-8 p-5 md:p-8">
      <ProductHeader
        :title="item.data.value?.title ?? 'Товар без названия'"
        :kind="item.data.value ? kindLabels[item.data.value.kind] : undefined"
        :status="
          item.data.value ? statusLabels[item.data.value.own.status] : undefined
        "
        :sku="item.data.value?.own.sku"
        editing
        :locale="ctx.locale.value"
        :options="ctx.options.value"
        @back="ctx.router.push('/catalog/items')"
        @locale="ctx.selectLocale"
        @mode="
          ctx.router.push({
            path: `/catalog/items/${id}`,
            query: { locale: ctx.locale.value },
          })
        "
      />
      <Alert
        v-if="
          error ||
          item.isError.value ||
          schema.isError.value ||
          attributes.isError.value ||
          categories.isError.value ||
          tags.isError.value
        "
        variant="destructive"
        ><AlertTitle>{{
          conflict
            ? "Товар изменился в другом окне"
            : "Не удалось выполнить операцию"
        }}</AlertTitle
        ><AlertDescription
          >{{
            error ||
            getApiErrorMessage(
              item.error.value ||
                schema.error.value ||
                attributes.error.value ||
                categories.error.value ||
                tags.error.value,
              "Повторите загрузку.",
            )
          }}
          <p v-if="conflict">
            Ваш ввод сохранён. Загрузите актуальные данные, чтобы продолжить.
          </p>
          <Button variant="outline" :disabled="pending" @click="reload"
            >Загрузить актуальные данные</Button
          ></AlertDescription
        ></Alert
      >
      <Skeleton v-if="item.isPending.value" class="h-96 w-full" />
      <template v-if="item.data.value && item.data.value.kind !== 'variant'">
        <div class="grid min-w-0 gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
          <div class="flex min-w-0 flex-col gap-6">
            <ProductFieldsBlock
              :key="`${id}:${ctx.locale.value}:content`"
              :item="item.data.value"
              section="content"
              :locale="ctx.locale.value"
              :pending="blocked || !schemaVersion"
              :reset="resetFor(id, 'content')"
              :attributes="attributes.data.value ?? []"
              :schema-version="schemaVersion"
              :dirty="isDirty(id, 'content')"
              @dirty="mark(id, 'content', $event)"
              @save="save(id, 'content', $event)"
            />
            <Card class="min-w-0 shadow-none"
              ><CardHeader
                ><CardTitle>Данные товара</CardTitle
                ><CardDescription
                  >Настройки сгруппированы по разделам. Каждый блок сохраняется
                  отдельно.</CardDescription
                ></CardHeader
              ><CardContent class="min-w-0">
                <Tabs
                  :model-value="tab"
                  orientation="vertical"
                  class="flex flex-col gap-5 md:flex-row"
                  @update:model-value="selectTab(String($event))"
                >
                  <TabsList
                    class="hidden h-auto w-44 shrink-0 self-start flex-col items-stretch justify-start gap-1 bg-transparent p-0 md:sticky md:top-4 md:flex"
                    aria-label="Данные товара"
                    ><TabsTrigger
                      v-for="t in tabs"
                      :key="t.id"
                      :value="t.id"
                      :aria-label="t.label"
                      class="h-auto min-h-10 w-full flex-none justify-start px-3 py-2.5"
                      >{{ t.label
                      }}<span
                        v-if="dirtyTab(t.id)"
                        class="ml-auto"
                        aria-hidden="true"
                        >•</span
                      ></TabsTrigger
                    ></TabsList
                  >
                  <label class="flex flex-col gap-2 text-sm md:hidden"
                    >Раздел данных товара<select
                      :value="tab"
                      aria-label="Раздел данных товара"
                      class="w-full rounded-md border bg-background p-2"
                      @change="
                        selectTab(($event.target as HTMLSelectElement).value)
                      "
                    >
                      <option v-for="t in tabs" :key="t.id" :value="t.id">
                        {{ t.label }}{{ dirtyTab(t.id) ? " •" : "" }}
                      </option>
                    </select></label
                  >
                  <div class="flex min-w-0 flex-1 flex-col gap-5">
                    <template v-for="group in rootGroups" :key="group.tab"
                      ><TabsContent
                        :value="group.tab"
                        force-mount
                        v-show="tab === group.tab"
                        class="flex flex-col gap-5"
                        :aria-label="
                          productTabs.find((t) => t.id === group.tab)?.label
                        "
                      >
                        <template
                          v-for="section in group.sections"
                          :key="section"
                          ><ProductFieldsBlock
                            v-if="
                              !(
                                item.data.value.kind === 'variable' &&
                                (section === 'price' ||
                                  section === 'virtual' ||
                                  section === 'sku')
                              )
                            "
                            :key="`${id}:${ctx.locale.value}:${section}`"
                            :item="item.data.value"
                            :section="section"
                            :locale="ctx.locale.value"
                            :pending="
                              blocked ||
                              (section === 'attributes' &&
                                isDirty(id, 'structure'))
                            "
                            :reset="resetFor(id, section)"
                            :attributes="attributes.data.value ?? []"
                            :schema-version="schemaVersion"
                            :dirty="isDirty(id, section)"
                            @dirty="mark(id, section, $event)"
                            @save="
                              save(id, section, $event)
                            " /></template></TabsContent
                    ></template>
                    <div
                      v-show="tab === 'additional'"
                      class="flex flex-col gap-3 border-t pt-5"
                    >
                      <h3 class="font-medium">Изменение вида товара</h3>
                      <p class="text-sm text-muted-foreground">
                        Преобразование меняет структуру семьи. Сначала сохраните
                        или отмените остальные изменения.
                      </p>
                      <Button
                        variant="outline"
                        :disabled="
                          blocked ||
                          Object.values(draft.dirty).some(Boolean) ||
                          !!item.data.value.own.category_ids.length ||
                          !!item.data.value.own.tag_ids.length
                        "
                        @click="openTransition"
                        >{{
                          item.data.value.kind === "simple"
                            ? "Преобразовать в товар с вариантами"
                            : "Преобразовать в простой товар"
                        }}</Button
                      >
                      <p
                        v-if="
                          item.data.value.kind === 'simple' &&
                          (item.data.value.own.category_ids.length ||
                            item.data.value.own.tag_ids.length)
                        "
                        class="text-sm text-muted-foreground"
                      >
                        Перед преобразованием снимите категории и метки.
                      </p>
                    </div>
                    <template v-if="item.data.value.kind === 'variable'">
                      <div
                        v-show="tab === 'attributes' || tab === 'variants'"
                        class="flex flex-col gap-4"
                      >
                        <div
                          class="flex flex-wrap items-center justify-between gap-3"
                        >
                          <h3 class="font-medium">Структура вариантов</h3>
                          <Button
                            v-if="!structureRequested"
                            variant="outline"
                            :disabled="blocked || isDirty(id, 'attributes')"
                            @click="structureRequested = true"
                            >Изменить структуру</Button
                          >
                        </div>
                        <p class="text-sm text-muted-foreground">
                          Характеристики вариантов и комбинации сохраняются
                          вместе. Для использования общей характеристики в
                          вариантах сначала уберите её обычное назначение.
                        </p>
                        <Alert
                          v-if="allVariants.isError.value"
                          variant="destructive"
                          ><AlertTitle
                            >Не удалось загрузить структуру</AlertTitle
                          ><AlertDescription
                            ><Button
                              variant="outline"
                              @click="allVariants.refetch()"
                              >Повторить</Button
                            ></AlertDescription
                          ></Alert
                        >
                        <Skeleton
                          v-if="
                            structureRequested && allVariants.isPending.value
                          "
                          class="h-32 w-full"
                        />
                        <CatalogItemStructureForm
                          v-if="structure"
                          :key="`${id}:${ctx.locale.value}:structure`"
                          :initial="structure"
                          :attributes="structureAttributes"
                          :pending="
                            blocked ||
                            isDirty(id, 'attributes') ||
                            Object.entries(draft.dirty).some(
                              ([key, value]) =>
                                !key.startsWith(`${id}:`) && value,
                            )
                          "
                          :reset="resetFor(id, 'structure')"
                          :part="tab === 'attributes' ? 'axes' : 'combinations'"
                          @dirty="mark(id, 'structure', $event)"
                          @submit="replaceStructure"
                        />
                      </div>
                      <TabsContent
                        value="variants"
                        force-mount
                        v-show="tab === 'variants'"
                        class="flex min-w-0 flex-col gap-5"
                      >
                        <Alert
                          v-if="variants.isError.value"
                          variant="destructive"
                          ><AlertTitle>Не удалось загрузить варианты</AlertTitle
                          ><AlertDescription
                            ><Button
                              variant="outline"
                              @click="variants.refetch()"
                              >Повторить</Button
                            ></AlertDescription
                          ></Alert
                        >
                        <div>
                          <div v-for="row in rows" :key="row.item.id">
                            <ProductVariantRow
                              :row="row"
                              :selected="variantId === row.item.id"
                              editing
                              :dirty="!!dirtySections(row.item.id).length"
                              @select="
                                selectVariant(
                                  variantId === row.item.id ? '' : row.item.id,
                                )
                              "
                            />
                            <div :id="`variant-editor-${row.item.id}`" />
                          </div>
                        </div>
                        <div
                          class="flex flex-wrap items-center justify-end gap-2"
                        >
                          <span class="text-xs text-muted-foreground"
                            >{{ offset + 1 }}–{{ offset + rows.length }} из
                            {{ variants.data.value?.total ?? 0 }}</span
                          ><Button
                            variant="outline"
                            size="sm"
                            :disabled="!offset || variants.isFetching.value"
                            @click="offset -= 20"
                            >Назад</Button
                          ><Button
                            variant="outline"
                            size="sm"
                            :disabled="
                              offset + 20 >=
                                (variants.data.value?.total ?? 0) ||
                              variants.isFetching.value
                            "
                            @click="offset += 20"
                            >Далее</Button
                          >
                        </div>
                        <Alert
                          v-if="variantId && variant.isError.value"
                          variant="destructive"
                          ><AlertTitle>Вариант недоступен</AlertTitle
                          ><AlertDescription
                            >Вариант удалён или принадлежит другому
                            товару.<Button
                              variant="outline"
                              @click="selectVariant('')"
                              >Вернуться к родителю</Button
                            ></AlertDescription
                          ></Alert
                        >
                        <Skeleton
                          v-if="variantId && variant.isPending.value"
                          class="h-32 w-full"
                        />
                        <div id="direct-variant-editor" />
                        <Teleport
                          v-for="child in Object.values(visited)"
                          :key="`${child.id}:${ctx.locale.value}`"
                          defer
                          :to="
                            rows.some((row) => row.item.id === child.id)
                              ? `#variant-editor-${child.id}`
                              : '#direct-variant-editor'
                          "
                        >
                          <ProductVariantEditor
                            v-show="variantId === child.id"
                            :item="child"
                            :label="
                              selectionLabel(child, attributes.data.value ?? [])
                            "
                            :locale="ctx.locale.value"
                            :pending="blocked || !schemaVersion"
                            :structure-dirty="isDirty(id, 'structure')"
                            :schema-version="schemaVersion"
                            :attributes="attributes.data.value ?? []"
                            :dirty-sections="dirtySections(child.id)"
                            :resets="resets(child.id)"
                            :image-url="
                              (imageId) => imageUrl(child.id, imageId)
                            "
                            @dirty="
                              (section, value) => mark(child.id, section, value)
                            "
                            @save="
                              (section, value) => save(child.id, section, value)
                            "
                            @inherit="inherit(child.id, $event)"
                            @upload="
                              (file, main) => upload(child.id, file, main)
                            "
                        /></Teleport>
                      </TabsContent>
                    </template>
                  </div>
                </Tabs> </CardContent
            ></Card>
          </div>
          <ProductEditorSidebar
            :item="item.data.value"
            :locale="ctx.locale.value"
            :pending="pending"
            :blocked="blocked"
            :schema-version="schemaVersion"
            :categories="categories.data.value ?? []"
            :tags="tags.data.value ?? []"
            :dirty-sections="
              sidebarSections.filter((section) => isDirty(id, section))
            "
            :resets="
              Object.fromEntries(
                sidebarSections.map((section) => [
                  section,
                  resetFor(id, section),
                ]),
              )
            "
            :image-url="(imageId) => imageUrl(id, imageId)"
            @dirty="(section, value) => mark(id, section, value)"
            @save="(section, value) => save(id, section, value)"
            @upload="(file, main) => upload(id, file, main)"
            @reload="reload"
          />
        </div>
      </template>
      <Dialog :open="transition" @update:open="closeTransition"
        ><DialogContent class="max-h-[85vh] overflow-y-auto sm:max-w-2xl"
          ><DialogHeader
            ><DialogTitle>Изменить вид товара</DialogTitle
            ><DialogDescription
              >Проверьте комбинации и выберите вариант, значения которого нужно
              сохранить.</DialogDescription
            ></DialogHeader
          >
          <Alert v-if="error" variant="destructive"
            ><AlertTitle>Не удалось изменить вид товара</AlertTitle
            ><AlertDescription>{{ error }}</AlertDescription></Alert
          >
          <CatalogItemStructureForm
            v-if="item.data.value?.kind === 'simple'"
            :initial="null"
            :attributes="structureAttributes"
            :pending="blocked"
            :reset="0"
            carry
            submit-label="Преобразовать в товар с вариантами"
            @dirty="mark(id, 'kind', $event)"
            @submit="toVariable"
          />
          <template v-else
            ><label class="flex flex-col gap-2 text-sm"
              >Сохраняемый вариант<select
                v-model="selectedChild"
                class="w-full rounded-md border bg-background p-2"
              >
                <option value="">Выберите вариант</option>
                <option
                  v-for="child in allVariants.data.value ?? []"
                  :key="child.id"
                  :value="child.id"
                >
                  {{ selectionLabel(child, attributes.data.value ?? []) }}
                </option>
              </select></label
            ><Button :disabled="blocked || !selectedChild" @click="toSimple"
              >Преобразовать в простой товар</Button
            ></template
          >
        </DialogContent></Dialog
      >
    </div>
  </div>
</template>
