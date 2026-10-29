<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from "vue";
import "./product.css";
import { FileText, Layers, Radio } from "@lucide/vue";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import type { ProductEditorTab } from "../../model/product-editor-state";
import { useProductSectionDraft } from "../../model/use-product-section-draft";
import { Button } from "@/components/ui/button";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import type { CatalogItem } from "../../model/catalog.types";
import type { ProductStock } from "../../model/product.types";
import type { ProductSection } from "../../model/product.types";
import {
  editorGroups,
  type EditorGroup,
} from "../../model/product-editor-layout";

import ProductEditorSection from "./ProductEditorSection.vue";
import ProductIdentityForm from "../forms/ProductIdentityForm.vue";
import ProductStatusForm from "../forms/ProductStatusForm.vue";
import ProductPricingForm from "../forms/ProductPricingForm.vue";
import ProductStockForm from "../forms/ProductStockForm.vue";
import ProductDescriptionsForm from "../forms/ProductDescriptionsForm.vue";
import CatalogItemGalleryForm from "../forms/CatalogItemGalleryForm.vue";
import ProductMeasurementsForm from "../forms/ProductMeasurementsForm.vue";
const props = defineProps<{
  item: CatalogItem;
  parentStock?: ProductStock;
  content: Record<string, string>;
  disabled: boolean;
  contentDisabled: boolean;
  errors: Partial<Record<ProductSection, string>>;
  dirty: ProductSection[];
  resets: Partial<Record<ProductSection, number>>;
  pending: boolean;
  uploading: boolean;
  saveStatus: string;
  error: string;
  activeTab: ProductEditorTab;
  initialGroup?: EditorGroup;
  focusTitle?: boolean;
  imageUrl: (id: string) => string;
}>();
const emit = defineEmits<{
  save: [section: ProductSection, value: Record<string, unknown>];
  content: [code: "title" | "body", value: string | undefined];
  upload: [file: File, main: boolean];
  reload: [];
  retry: [];
  focused: [];
  tab: [value: ProductEditorTab];
}>();
const { value: virtual, change: changeVirtual } = useProductSectionDraft(
  () => props.item.virtual,
  () => props.resets.virtual ?? 0,
  (value) => emit("save", "virtual", { virtual: value }),
);
const availableGroups = computed(() =>
  editorGroups.filter(
    (group) =>
      !(group.id === "measurements" && virtual.value) &&
      !(group.id === "pricing" && props.item.kind === "variable"),
  ),
);
const root = ref<HTMLElement | null>(null);
const revealed = reactive<Partial<Record<EditorGroup, number>>>({});
let titleFocused = false;
async function focusTitleField(): Promise<void> {
  if (
    titleFocused ||
    !props.focusTitle ||
    props.contentDisabled ||
    props.disabled
  )
    return;
  await nextTick();
  const input = root.value?.querySelector<HTMLInputElement>(
    "[data-product-title]",
  );
  if (input && !input.disabled) {
    input.focus();
    titleFocused = true;
    emit("focused");
  }
}
watch(
  () => [props.contentDisabled, props.disabled],
  () => {
    void focusTitleField();
  },
);
const groupDirty = (id: EditorGroup): boolean =>
  editorGroups
    .find((g) => g.id === id)
    ?.sections.some((s) => props.dirty.includes(s)) ?? false;
const groupError = (id: EditorGroup): string =>
  editorGroups
    .find((g) => g.id === id)
    ?.sections.map((s) => props.errors[s])
    .find(Boolean) ?? "";
const invalidGroups = computed(() =>
  availableGroups.value.filter(
    (g) => groupError(g.id) && g.id !== "descriptions",
  ),
);
let pendingNavigation: { id: EditorGroup; focus: boolean } | undefined;
watch(
  () => props.activeTab,
  () => {
    if (!pendingNavigation) return;
    const target = pendingNavigation;
    pendingNavigation = undefined;
    void navigate(target.id, target.focus);
  },
);
async function navigate(id: EditorGroup, focus = false): Promise<void> {
  if (!availableGroups.value.some((group) => group.id === id)) return;
  if (id === "descriptions") {
    const tab = "description";
    if (props.activeTab !== tab) {
      pendingNavigation = { id, focus };
      emit("tab", tab);
      return;
    }
  }
  revealed[id] = (revealed[id] ?? 0) + 1;
  await nextTick();
  const target = root.value?.querySelector<HTMLElement>(
    `#product-${props.item.id}-${id}`,
  );
  // Scroll the editor pane only; scrollIntoView can also move the app shell.
  let container = target?.parentElement;
  while (target && container) {
    if (
      ["auto", "scroll"].includes(getComputedStyle(container).overflowY) &&
      container.scrollHeight > container.clientHeight
    ) {
      container.scrollTo({
        top:
          container.scrollTop +
          target.getBoundingClientRect().top -
          container.getBoundingClientRect().top -
          16,
        behavior: "instant",
      });
      break;
    }
    container = container.parentElement;
  }
  if (focus) {
    const controls = [
      ...Array.from(
        target?.querySelectorAll<HTMLElement>('[aria-invalid="true"]') ?? [],
      ),
      ...Array.from(
        target?.querySelectorAll<HTMLElement>(
          'input:not([type="hidden"]), [role="combobox"], [contenteditable="true"], button',
        ) ?? [],
      ),
    ];
    const control = controls.find(
      (el) =>
        el.getClientRects().length &&
        !el.matches(':disabled,[aria-disabled="true"]'),
    );
    control?.focus({ preventScroll: true });
  }
}
watch(
  () => props.initialGroup,
  (id) => {
    if (id) void navigate(id);
  },
);
onMounted(async () => {
  if (props.focusTitle) {
    await focusTitleField();
  } else if (props.initialGroup) await navigate(props.initialGroup);
});
</script>
<template>
  <div
    ref="root"
    class="product-editor product-workspace min-h-0 min-w-0 flex-1"
  >
    <section
      class="product-workspace-fields"
      aria-label="Основная информация о товаре"
    >
      <div v-if="error || invalidGroups.length" class="px-4 pt-3">
        <Alert variant="destructive">
          <AlertTitle>{{
            error ? "Не удалось сохранить изменения" : "Проверьте поля"
          }}</AlertTitle>
          <AlertDescription>
            <p>
              {{
                error || "Ввод сохранён в редакторе. Исправьте отмеченные поля."
              }}
            </p>
            <Button
              v-if="error"
              type="button"
              variant="outline"
              :disabled="pending"
              @click="emit('retry')"
              >Повторить</Button
            >
            <Button
              v-for="group in invalidGroups"
              :key="group.id"
              type="button"
              variant="link"
              class="h-auto whitespace-normal px-0 text-left"
              @click="navigate(group.id, true)"
              >Перейти к ошибке: {{ group.title }}</Button
            >
          </AlertDescription>
        </Alert>
      </div>
      <div class="px-4 pb-4">
        <ProductEditorSection
          :id="`product-${item.id}-status`"
          title="Статус"
          :dirty="groupDirty('status')"
          :error="groupError('status')"
          :reveal="revealed.status"
        >
          <ProductStatusForm
            :id="item.id"
            :status="item.status"
            :disabled="disabled"
            :pending="pending || (groupDirty('status') && !props.errors.status)"
            :error="props.errors.status"
            @change="emit('save', 'status', { status: $event })"
          />
        </ProductEditorSection>
        <ProductEditorSection
          :id="`product-${item.id}-identity`"
          title="Основные сведения"
          collapsible
          default-open
          :dirty="groupDirty('identity')"
          :error="groupError('identity')"
          :reveal="revealed.identity"
        >
          <ProductIdentityForm
            :item="item"
            :virtual="virtual"
            :content="content"
            :disabled="disabled"
            :content-disabled="contentDisabled"
            :errors="props.errors"
            :resets="resets"
            @title="emit('content', 'title', $event)"
            @virtual="changeVirtual"
            @save="(section, value) => emit('save', section, value)"
          />
        </ProductEditorSection>
        <ProductEditorSection
          v-if="item.kind !== 'variable'"
          :id="`product-${item.id}-pricing`"
          title="Цены"
          collapsible
          default-open
          :dirty="groupDirty('pricing')"
          :error="groupError('pricing')"
          :reveal="revealed.pricing"
        >
          <ProductPricingForm
            :id="item.id"
            :value="item.price_specification"
            :current="item.price"
            :reset="resets.price ?? 0"
            :disabled="disabled"
            :error="props.errors.price"
            @change="emit('save', 'price', { price: $event })"
          />
        </ProductEditorSection>
        <ProductEditorSection
          :id="`product-${item.id}-stock`"
          :title="item.kind === 'variable' ? 'Общий остаток' : 'Наличие'"
          collapsible
          default-open
          :dirty="groupDirty('stock')"
          :error="groupError('stock')"
          :reveal="revealed.stock"
        >
          <ProductStockForm
            :id="item.id"
            :value="item.stock"
            :current="item.stock_status"
            :reset="resets.stock ?? 0"
            :disabled="disabled"
            :kind="item.kind"
            :parent-stock="parentStock"
            :error="props.errors.stock"
            @change="emit('save', 'stock', { stock: $event })"
          />
        </ProductEditorSection>
        <ProductEditorSection
          v-show="!virtual"
          :id="`product-${item.id}-measurements`"
          title="Вес и размеры"
          collapsible
          :summary="
            item.weight || Object.values(item.dimensions ?? {}).some(Boolean)
              ? 'Есть заполненные значения'
              : 'Не заданы'
          "
          :dirty="groupDirty('measurements')"
          :error="groupError('measurements')"
          :reveal="revealed.measurements"
        >
          <ProductMeasurementsForm
            :item="item"
            :disabled="disabled"
            :reset="resets.measurements ?? 0"
            :error="props.errors.measurements"
            @change="emit('save', 'measurements', { ...$event })"
          />
        </ProductEditorSection>
        <ProductEditorSection
          :id="`product-${item.id}-media`"
          title="Галерея"
          collapsible
          default-open
          :dirty="groupDirty('media')"
          :error="groupError('media')"
          :reveal="revealed.media"
        >
          <CatalogItemGalleryForm
            :value="item.gallery"
            :pending="disabled || uploading"
            :uploading="uploading"
            :reset="resets.galleries ?? 0"
            :validation-error="props.errors.galleries"
            :image-url="imageUrl"
            @save="emit('save', 'galleries', { gallery: $event })"
            @upload="(file, main) => emit('upload', file, main)"
          />
        </ProductEditorSection>
      </div>
    </section>
    <Tabs
      :model-value="activeTab"
      class="product-workspace-related min-w-0 gap-0"
      @update:model-value="emit('tab', $event as ProductEditorTab)"
    >
      <div
        class="product-workspace-tabs min-w-0 shrink-0 overflow-x-auto bg-background"
      >
        <TabsList variant="line" aria-label="Данные товара">
          <TabsTrigger value="description" variant="line"
            ><FileText class="mr-2 size-4" aria-hidden="true" />Описание<Badge
              v-if="props.errors.content"
              variant="destructive"
              class="ml-2"
              >!</Badge
            ></TabsTrigger
          >
          <TabsTrigger
            v-if="$slots.variants && item.kind === 'variable'"
            value="variants"
            variant="line"
            ><Layers class="mr-2 size-4" aria-hidden="true" />Варианты ·
            {{ item.variant_count ?? 0 }}</TabsTrigger
          >
          <TabsTrigger
            v-if="$slots.publications"
            value="publications"
            variant="line"
            ><Radio
              class="mr-2 size-4"
              aria-hidden="true"
            />Публикации</TabsTrigger
          >
        </TabsList>
      </div>
      <TabsContent
        value="description"
        force-mount
        v-show="activeTab === 'description'"
        class="product-workspace-panel"
      >
        <ProductEditorSection
          :id="`product-${item.id}-descriptions`"
          title="Описание"
          :dirty="groupDirty('descriptions')"
          :error="groupError('descriptions')"
        >
          <ProductDescriptionsForm
            :content="content"
            :variant="item.kind === 'variant'"
            :disabled="disabled || contentDisabled"
            :error="props.errors.content"
            @change="(code, value) => emit('content', code, value)"
          />
        </ProductEditorSection>
      </TabsContent>
      <TabsContent
        v-if="$slots.variants && item.kind === 'variable'"
        value="variants"
        class="product-workspace-panel product-workspace-variants"
        ><slot name="variants"
      /></TabsContent>
      <TabsContent
        v-if="$slots.publications"
        value="publications"
        class="product-workspace-panel product-workspace-publications"
        ><slot name="publications"
      /></TabsContent>
    </Tabs>
  </div>
</template>
