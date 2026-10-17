<script setup lang="ts">
import { computed } from "vue";
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
import { getApiErrorMessage } from "@/app/providers/http";
import { useProductPage } from "../../model/use-product-page";
import { productTabs, statusLabels } from "../../model/product-presentation";
import type { ProductSection } from "../../model/product.types";
import ProductHeader from "../product/ProductHeader.vue";
import ProductFieldsBlock from "../product/ProductFieldsBlock.vue";
import ProductEditorSidebar from "../product/ProductEditorSidebar.vue";
const {
  ctx,
  id,
  item,
  attributes,
  categories,
  tags,
  schema,
  tab,
  selectTab,
  pending,
  error,
  blocked,
  isDirty,
  resetFor,
  save,
  upload,
  reload,
  imageUrl,
  fieldError,
  saveStatus,
  retry,
  uploading,
} = useProductPage(true);
const schemaVersion = computed(
  () => schema.data.value?.schema.schema_version ?? 0,
);
const groups = [
  { tab: "general", sections: ["price", "virtual"] },
  { tab: "inventory", sections: ["sku", "stock"] },
  { tab: "shipping", sections: ["measurements"] },
  { tab: "attributes", sections: ["attributes"] },
  { tab: "additional", sections: ["metadata"] },
] as const;
const sidebarSections: ProductSection[] = [
  "status",
  "galleries",
  "categories",
  "tags",
];
const dirtyTab = (value: string) =>
  groups
    .find((group) => group.tab === value)
    ?.sections.some((section) => isDirty(section)) ?? false;
</script>
<template>
  <div class="min-h-0 flex-1 overflow-y-auto">
    <div class="mx-auto flex w-full max-w-[1440px] flex-col gap-8 p-5 md:p-8">
      <ProductHeader
        :title="item.data.value?.title ?? 'Товар без названия'"
        :status="
          item.data.value ? statusLabels[item.data.value.status] : undefined
        "
        :sku="item.data.value?.sku"
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
      <p
        role="status"
        aria-live="polite"
        class="text-sm text-muted-foreground"
        data-testid="autosave-status"
      >
        {{ saveStatus }}
      </p>
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
      >
        <AlertTitle>{{ "Не удалось выполнить операцию" }}</AlertTitle>
        <AlertDescription>
          {{
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
          <Button
            v-if="error"
            variant="outline"
            :disabled="pending"
            @click="retry"
            >Повторить</Button
          >
          <Button variant="outline" :disabled="pending" @click="reload"
            >Загрузить актуальные данные</Button
          >
        </AlertDescription>
      </Alert>
      <Skeleton v-if="item.isPending.value" class="h-96 w-full" />
      <div
        v-if="item.data.value"
        class="grid min-w-0 gap-6 xl:grid-cols-[minmax(0,1fr)_320px]"
      >
        <div class="flex min-w-0 flex-col gap-6">
          <ProductFieldsBlock
            :key="`${ctx.sessionKey.value}:${id}:${ctx.locale.value}:content`"
            :item="item.data.value"
            section="content"
            :locale="ctx.locale.value"
            :pending="blocked || !schemaVersion"
            :reset="resetFor('content')"
            :attributes="attributes.data.value ?? []"
            :schema-version="schemaVersion"
            :dirty="isDirty('content')"
            :validation-error="fieldError('content')"
            @save="save('content', $event)"
          />
          <Card class="min-w-0 shadow-none">
            <CardHeader
              ><CardTitle>Данные товара</CardTitle
              ><CardDescription
                >Изменения сохраняются автоматически после короткой
                паузы.</CardDescription
              ></CardHeader
            >
            <CardContent class="min-w-0">
              <Tabs
                :model-value="tab"
                orientation="vertical"
                class="flex flex-col gap-5 md:flex-row"
                @update:model-value="selectTab(String($event))"
              >
                <TabsList
                  class="hidden h-auto w-44 shrink-0 self-start flex-col items-stretch justify-start gap-1 bg-transparent p-0 md:sticky md:top-4 md:flex"
                  aria-label="Данные товара"
                >
                  <TabsTrigger
                    v-for="entry in productTabs"
                    :key="entry.id"
                    :value="entry.id"
                    :aria-label="entry.label"
                    class="h-auto min-h-10 w-full flex-none justify-start px-3 py-2.5"
                    >{{ entry.label
                    }}<span
                      v-if="dirtyTab(entry.id)"
                      class="ml-auto"
                      aria-hidden="true"
                      >•</span
                    ></TabsTrigger
                  >
                </TabsList>
                <label class="flex flex-col gap-2 text-sm md:hidden"
                  >Раздел данных товара<select
                    :value="tab"
                    aria-label="Раздел данных товара"
                    class="w-full rounded-md border bg-background p-2"
                    @change="
                      selectTab(($event.target as HTMLSelectElement).value)
                    "
                  >
                    <option
                      v-for="entry in productTabs"
                      :key="entry.id"
                      :value="entry.id"
                    >
                      {{ entry.label }}{{ dirtyTab(entry.id) ? " •" : "" }}
                    </option>
                  </select></label
                >
                <div class="flex min-w-0 flex-1 flex-col gap-5">
                  <TabsContent
                    v-for="group in groups"
                    :key="group.tab"
                    :value="group.tab"
                    force-mount
                    v-show="tab === group.tab"
                    class="flex flex-col gap-5"
                    :aria-label="
                      productTabs.find((entry) => entry.id === group.tab)?.label
                    "
                  >
                    <ProductFieldsBlock
                      v-for="section in group.sections"
                      :key="`${ctx.sessionKey.value}:${id}:${ctx.locale.value}:${section}`"
                      :item="item.data.value"
                      :section="section"
                      :locale="ctx.locale.value"
                      :pending="
                        blocked ||
                        (section === 'attributes' && attributes.isError.value)
                      "
                      :reset="resetFor(section)"
                      :attributes="attributes.data.value ?? []"
                      :schema-version="schemaVersion"
                      :dirty="isDirty(section)"
                      :validation-error="fieldError(section)"
                      @save="save(section, $event)"
                    />
                  </TabsContent>
                </div>
              </Tabs>
            </CardContent>
          </Card>
        </div>
        <ProductEditorSidebar
          :key="`${ctx.sessionKey.value}:${id}:${ctx.locale.value}:sidebar`"
          :item="item.data.value"
          :locale="ctx.locale.value"
          :pending="pending"
          :uploading="uploading"
          :errors="
            Object.fromEntries(
              sidebarSections.map((section) => [section, fieldError(section)]),
            )
          "
          :blocked="blocked || categories.isError.value || tags.isError.value"
          :schema-version="schemaVersion"
          :categories="categories.data.value ?? []"
          :tags="tags.data.value ?? []"
          :dirty-sections="
            sidebarSections.filter((section) => isDirty(section))
          "
          :resets="
            Object.fromEntries(
              sidebarSections.map((section) => [section, resetFor(section)]),
            )
          "
          :image-url="imageUrl"
          @save="save"
          @upload="upload"
          @reload="reload"
        />
      </div>
    </div>
  </div>
</template>
