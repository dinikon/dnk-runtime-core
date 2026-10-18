<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from "vue";
import { Check, LoaderCircle, MoreHorizontal } from "@lucide/vue";
import { Button } from "@/components/ui/button";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Field, FieldLabel } from "@/components/ui/field";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { CatalogItem } from "../../model/catalog.types";
import type { ProductSection } from "../../model/product.types";
import {
  editorGroups,
  type EditorGroup,
} from "../../model/product-editor-layout";
import { useProductSectionDraft } from "../../model/use-product-section-draft";
import { statusLabels, stockLabels } from "../../model/product-presentation";
import ProductEditorSection from "./ProductEditorSection.vue";
import ProductEditorSections from "./ProductEditorSections.vue";
import ProductFieldError from "./ProductFieldError.vue";
import ProductIdentityForm from "../forms/ProductIdentityForm.vue";
import ProductPricingForm from "../forms/ProductPricingForm.vue";
import ProductStockForm from "../forms/ProductStockForm.vue";
import ProductDescriptionsForm from "../forms/ProductDescriptionsForm.vue";
import CatalogItemGalleryForm from "../forms/CatalogItemGalleryForm.vue";
import ProductMeasurementsForm from "../forms/ProductMeasurementsForm.vue";
const props = defineProps<{
  item: CatalogItem;
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
}>();
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
const { value: status, change: changeStatus } = useProductSectionDraft(
  () => props.item.status,
  () => props.resets.status ?? 0,
  (value) => emit("save", "status", { status: value }),
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
  editorGroups.filter((g) => groupError(g.id) && g.id !== "descriptions"),
);
function summary(id: EditorGroup, clean: string): string {
  return groupDirty(id) ? "Есть несохранённые изменения" : clean;
}
async function navigate(id: EditorGroup, focus = false): Promise<void> {
  revealed[id] = (revealed[id] ?? 0) + 1;
  await nextTick();
  const target = root.value?.querySelector<HTMLElement>(`#product-${id}`);
  target?.scrollIntoView({ block: "start", behavior: "instant" });
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
  <div ref="root" class="min-w-0">
    <div
      class="product-savebar flex flex-wrap items-center gap-3 border-y bg-background py-3"
    >
      <p
        role="status"
        aria-live="polite"
        data-testid="autosave-status"
        class="flex min-w-0 flex-1 items-center gap-2 text-sm text-muted-foreground"
      >
        <LoaderCircle
          v-if="pending"
          class="size-4 shrink-0 animate-spin"
          aria-hidden="true"
        /><Check
          v-else-if="!dirty.length && !error"
          class="size-4 shrink-0"
          aria-hidden="true"
        />{{ saveStatus }}
      </p>
      <ProductEditorSections @select="navigate" />
      <Field orientation="horizontal" class="w-auto gap-2"
        ><FieldLabel for="product-status" class="sr-only"
          >Статус товара</FieldLabel
        ><Select
          :model-value="status"
          :disabled="disabled"
          @update:model-value="changeStatus($event as CatalogItem['status'])"
          ><SelectTrigger
            id="product-status"
            class="min-h-11 w-32"
            :aria-invalid="!!props.errors.status || undefined"
            :aria-describedby="props.errors.status ? 'status-error' : undefined"
            ><SelectValue /></SelectTrigger
          ><SelectContent
            ><SelectGroup
              ><SelectItem
                v-for="(label, key) in statusLabels"
                :key="key"
                :value="key"
                >{{ label }}</SelectItem
              ></SelectGroup
            ></SelectContent
          ></Select
        ></Field
      >
      <DropdownMenu
        ><DropdownMenuTrigger as-child
          ><Button
            type="button"
            variant="ghost"
            size="icon"
            class="min-h-11 min-w-11"
            aria-label="Действия с карточкой"
            ><MoreHorizontal /></Button></DropdownMenuTrigger
        ><DropdownMenuContent align="end"
          ><DropdownMenuGroup
            ><DropdownMenuItem
              :disabled="pending"
              class="min-h-11"
              @select="emit('reload')"
              >Обновить данные товара</DropdownMenuItem
            ></DropdownMenuGroup
          ></DropdownMenuContent
        ></DropdownMenu
      >
    </div>
    <div
      v-if="error || invalidGroups.length || props.errors.status"
      class="pt-5"
    >
      <Alert variant="destructive"
        ><AlertTitle>{{
          error ? "Не удалось сохранить изменения" : "Проверьте поля"
        }}</AlertTitle
        ><AlertDescription
          ><p v-if="error">{{ error }}</p>
          <p v-else>Ввод сохранён в карточке. Исправьте отмеченные поля.</p>
          <Button
            v-if="error"
            type="button"
            variant="outline"
            class="min-h-11"
            :disabled="pending"
            @click="emit('retry')"
            >Повторить</Button
          ><Button
            v-for="group in invalidGroups"
            :key="group.id"
            type="button"
            variant="link"
            class="h-auto min-h-11 whitespace-normal px-0 text-left"
            @click="navigate(group.id, true)"
            >Перейти к ошибке: {{ group.title }}</Button
          ><ProductFieldError
            id="status-error"
            :error="props.errors.status" /></AlertDescription
      ></Alert>
    </div>
    <div class="product-editor-grid">
      <div class="min-w-0">
        <ProductEditorSection
          id="product-identity"
          title="Основные сведения"
          :dirty="groupDirty('identity')"
          :error="groupError('identity')"
          ><ProductIdentityForm
            :item="item"
            :content="content"
            :disabled="disabled"
            :content-disabled="contentDisabled"
            :errors="props.errors"
            :resets="resets"
            @title="emit('content', 'title', $event)"
            @save="(section, value) => emit('save', section, value)"
        /></ProductEditorSection>
        <ProductEditorSection
          id="product-pricing"
          title="Цена и наличие"
          collapsible
          :summary="
            summary(
              'pricing',
              `${item.price !== null ? `${item.price} ${item.price_specification?.currency ?? ''}` : 'Цена не задана'} · ${stockLabels[item.stock_status] ?? 'Наличие не задано'}`,
            )
          "
          :dirty="groupDirty('pricing')"
          :error="groupError('pricing')"
          :reveal="revealed.pricing"
          ><div class="flex min-w-0 flex-col gap-6">
            <ProductPricingForm
              :id="item.id"
              :value="item.price_specification"
              :current="item.price"
              :reset="resets.price ?? 0"
              :disabled="disabled"
              :error="props.errors.price"
              @change="emit('save', 'price', { price: $event })"
            /><ProductStockForm
              :id="item.id"
              :value="item.stock"
              :current="item.stock_status"
              :reset="resets.stock ?? 0"
              :disabled="disabled"
              :error="props.errors.stock"
              @change="emit('save', 'stock', { stock: $event })"
            /></div
        ></ProductEditorSection>
        <ProductEditorSection
          id="product-media"
          title="Изображения"
          collapsible
          :summary="
            summary(
              'media',
              item.gallery?.images.length
                ? `Изображений: ${item.gallery.images.length}`
                : 'Добавить изображения',
            )
          "
          :dirty="groupDirty('media')"
          :error="groupError('media')"
          :reveal="revealed.media"
          ><CatalogItemGalleryForm
            :value="item.gallery"
            :pending="disabled || uploading"
            :uploading="uploading"
            :reset="resets.galleries ?? 0"
            :validation-error="props.errors.galleries"
            :image-url="imageUrl"
            @save="emit('save', 'galleries', { gallery: $event })"
            @upload="(file, main) => emit('upload', file, main)"
        /></ProductEditorSection>
        <ProductEditorSection
          id="product-descriptions"
          title="Описание"
          :dirty="groupDirty('descriptions')"
          :error="groupError('descriptions')"
          ><ProductDescriptionsForm
            :content="content"
            :disabled="disabled || contentDisabled"
            :error="props.errors.content"
            @change="(code, value) => emit('content', code, value)"
        /></ProductEditorSection>
      </div>
      <aside class="min-w-0" aria-label="Дополнительные сведения о товаре">
        <ProductEditorSection
          id="product-measurements"
          title="Вес и размеры"
          collapsible
          :summary="
            summary(
              'measurements',
              item.weight || Object.values(item.dimensions ?? {}).some(Boolean)
                ? 'Есть заполненные значения'
                : 'Не заданы',
            )
          "
          :dirty="groupDirty('measurements')"
          :error="groupError('measurements')"
          :reveal="revealed.measurements"
          ><ProductMeasurementsForm
            :item="item"
            :disabled="disabled"
            :reset="resets.measurements ?? 0"
            :error="props.errors.measurements"
            @change="emit('save', 'measurements', { ...$event })"
        /></ProductEditorSection>
      </aside>
    </div>
  </div>
</template>
