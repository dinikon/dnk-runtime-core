<script setup lang="ts">
import { Button } from "@/components/ui/button";
import { NativeSelect } from "@/components/ui/native-select";
import CatalogCategoryForm from "../forms/CatalogCategoryForm.vue";
import CatalogCategoryTree from "../results/CatalogCategoryTree.vue";
import { useCategoryPage } from "../../model/use-category-page";
const {
  ctx,
  query,
  options,
  editing,
  selected,
  dirty,
  saving,
  error,
  open,
  save,
  remove,
} = useCategoryPage();
</script>
<template>
  <div class="space-y-4">
    <header class="flex flex-wrap items-center gap-4">
      <h1 class="mr-auto text-xl font-semibold">Категории</h1>
      <label class="flex items-center gap-2 text-sm"
        >Язык
        <NativeSelect
          aria-label="Язык"
          :model-value="ctx.locale.value"
          :disabled="saving"
          @update:model-value="ctx.selectLocale(String($event))"
        >
          <option
            v-for="option in ctx.options.value"
            :key="option.code"
            :value="option.code"
          >
            {{ option.name }}
          </option>
        </NativeSelect></label
      >
      <Button :disabled="saving || !ctx.active.value" @click="open('new')"
        >Новая категория</Button
      >
    </header>
    <p v-if="query.isPending.value" role="status">Загрузка категорий…</p>
    <div v-else-if="query.isError.value" role="alert">
      Не удалось загрузить категории.
      <Button variant="outline" @click="query.refetch()">Повторить</Button>
    </div>
    <template v-else>
      <CatalogCategoryForm
        v-if="editing"
        :key="editing + ctx.locale.value + ctx.sessionKey.value"
        :node="selected"
        :options="options"
        :locale="ctx.locale.value"
        :pending="saving"
        :error="error"
        @dirty="dirty = $event"
        @cancel="open(null)"
        @save="save"
      />
      <p v-else-if="error" role="alert" class="text-destructive">{{ error }}</p>
      <CatalogCategoryTree
        v-if="options.length"
        :options="options"
        :disabled="saving || !!editing || !ctx.active.value"
        @edit="open($event.id)"
        @remove="remove"
        @make-default="save({ action: 'default', id: $event.id })"
      />
      <p v-else>Категорий пока нет.</p>
    </template>
  </div>
</template>
