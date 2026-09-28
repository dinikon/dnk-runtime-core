<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { refDebounced } from "@vueuse/core";
import { useInfiniteQuery } from "@tanstack/vue-query";
import { Plus, X, ExternalLink } from "@lucide/vue";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Field, FieldLabel, FieldDescription } from "@/components/ui/field";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Spinner } from "@/components/ui/spinner";
import { crmLinksApi } from "../../api/crm.api";
import type { CrmLink, Page } from "../../model/crm.types";

const props = defineProps<{
  modelValue: CrmLink[];
  original: CrmLink[];
  kind: "contacts" | "companies";
  ownerId?: string;
  pending: boolean;
}>();
const emit = defineEmits<{
  "update:modelValue": [items: CrmLink[]];
  navigate: [id: string];
}>();
const open = ref(false);
const search = ref("");
const debounced = refDebounced(search, 300);
const title = computed(() =>
  props.kind === "companies" ? "Компании" : "Контакты",
);
watch(
  () => props.ownerId,
  () => {
    open.value = false;
    search.value = "";
  },
);
const candidates = useInfiniteQuery({
  queryKey: computed(() => [
    "crm",
    "relation-options",
    props.kind,
    props.ownerId ?? "new",
    debounced.value.trim(),
  ]),
  enabled: computed(() => open.value && !props.pending),
  initialPageParam: 0,
  queryFn: async ({ pageParam, signal }): Promise<Page<CrmLink>> => {
    const params = { q: debounced.value.trim(), limit: 25, offset: pageParam };
    if (props.kind === "companies") {
      const page = await crmLinksApi.companies(props.ownerId, params, signal);
      return {
        ...page,
        items: page.items.map((item) => ({ id: item.id, name: item.name })),
      };
    }
    const page = await crmLinksApi.contacts(props.ownerId, params, signal);
    return {
      ...page,
      items: page.items.map((item) => ({
        id: item.id,
        name: item.displayName,
      })),
    };
  },
  getNextPageParam: (page) =>
    page.offset + page.limit < page.total
      ? page.offset + page.limit
      : undefined,
});
const choices = computed(() => {
  const selected = new Set(props.modelValue.map((item) => item.id));
  const options = new Map<string, CrmLink>();
  for (const item of props.original) {
    if (
      item.name
        .toLocaleLowerCase()
        .includes(debounced.value.trim().toLocaleLowerCase())
    )
      options.set(item.id, item);
  }
  for (const page of candidates.data.value?.pages ?? [])
    for (const item of page.items) options.set(item.id, item);
  return [...options.values()].filter((item) => !selected.has(item.id));
});
function add(item: CrmLink) {
  if (
    !props.pending &&
    !props.modelValue.some((selected) => selected.id === item.id)
  )
    emit("update:modelValue", [...props.modelValue, item]);
}
</script>
<template>
  <Field>
    <FieldLabel>{{ title }}</FieldLabel>
    <FieldDescription>Связи сохранятся вместе с карточкой.</FieldDescription>
    <ul
      v-if="modelValue.length"
      class="flex flex-col gap-2"
      :aria-label="`Связанные ${title.toLocaleLowerCase()}`"
    >
      <li
        v-for="item in modelValue"
        :key="item.id"
        class="flex min-w-0 items-center justify-between gap-2"
      >
        <Button
          type="button"
          variant="link"
          class="min-w-0 justify-start whitespace-normal text-left"
          :disabled="pending"
          @click="emit('navigate', item.id)"
        >
          <span class="break-words">{{ item.name }}</span
          ><ExternalLink data-icon="inline-end" />
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          :aria-label="`Удалить связь: ${item.name}`"
          :disabled="pending"
          @click="
            emit(
              'update:modelValue',
              modelValue.filter((selected) => selected.id !== item.id),
            )
          "
          ><X
        /></Button>
      </li>
    </ul>
    <p v-else class="text-sm text-muted-foreground">Связей пока нет.</p>
    <Popover v-model:open="open">
      <PopoverTrigger as-child
        ><Button
          type="button"
          variant="outline"
          class="self-start"
          :disabled="pending"
          ><Plus data-icon="inline-start" />{{
            kind === "companies" ? "Добавить компании" : "Добавить контакты"
          }}</Button
        ></PopoverTrigger
      >
      <PopoverContent
        align="start"
        class="flex max-w-[calc(100vw-3rem)] flex-col gap-2"
      >
        <Input
          v-model="search"
          :aria-label="`Поиск: ${title}`"
          placeholder="Поиск по имени или названию"
        />
        <div
          class="flex max-h-64 flex-col gap-1 overflow-y-auto"
          :aria-label="`Доступные ${title.toLocaleLowerCase()}`"
        >
          <Button
            v-for="item in choices"
            :key="item.id"
            type="button"
            variant="ghost"
            class="h-auto justify-start whitespace-normal text-left"
            :disabled="pending"
            @click="add(item)"
            ><Plus data-icon="inline-start" />{{ item.name }}</Button
          >
          <Spinner
            v-if="candidates.isFetching.value"
            class="self-center"
            aria-label="Загрузка вариантов"
          />
          <p
            v-if="
              !candidates.isFetching.value &&
              !candidates.isError.value &&
              !choices.length
            "
            class="py-2 text-sm text-muted-foreground"
          >
            {{
              candidates.hasNextPage.value
                ? "Варианты на этой странице уже выбраны."
                : "Нет доступных вариантов."
            }}
          </p>
          <Button
            v-if="candidates.isError.value"
            type="button"
            variant="outline"
            @click="candidates.refetch()"
            >Повторить загрузку вариантов</Button
          >
          <Button
            v-if="candidates.hasNextPage.value"
            type="button"
            variant="outline"
            :disabled="candidates.isFetching.value"
            @click="candidates.fetchNextPage()"
            >Показать ещё</Button
          >
        </div>
      </PopoverContent>
    </Popover>
  </Field>
</template>
