<script setup lang="ts">
import { Check, HardDrive, Search, X } from "@lucide/vue";
import { Button } from "@/components/ui/button";
import {
  InputGroup,
  InputGroupInput,
  InputGroupAddon,
} from "@/components/ui/input-group";
import {
  Popover,
  PopoverTrigger,
  PopoverContent,
} from "@/components/ui/popover";
import {
  Command,
  CommandInput,
  CommandEmpty,
  CommandList,
  CommandGroup,
  CommandItem,
} from "@/components/ui/command";
import {
  Select,
  SelectTrigger,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectValue,
} from "@/components/ui/select";
import {
  categoryLabels,
  bucketStatusLabels,
  type FileCategory,
  type StorageBucket,
} from "../model/types";
const props = defineProps<{
  search: string;
  buckets: StorageBucket[];
  selected: string[];
  category?: FileCategory;
}>();
const emit = defineEmits<{
  search: [value: string];
  buckets: [ids: string[]];
  category: [value?: FileCategory];
  reset: [];
}>();
function toggle(id: string): void {
  emit(
    "buckets",
    props.selected.includes(id)
      ? props.selected.filter((item) => item !== id)
      : [...props.selected, id].sort(),
  );
}
</script>
<template>
  <div class="flex flex-wrap items-center gap-3">
    <InputGroup class="min-w-0 flex-1 basis-64"
      ><InputGroupInput
        :model-value="search"
        maxlength="255"
        aria-label="Поиск по названию"
        placeholder="Поиск по названию…"
        @update:model-value="emit('search', String($event))" /><InputGroupAddon
        ><Search /></InputGroupAddon
    ></InputGroup>
    <Popover
      ><PopoverTrigger as-child
        ><Button variant="outline"
          ><HardDrive data-icon="inline-start" />{{
            selected.length ? `Диски: ${selected.length}` : "Все диски"
          }}</Button
        ></PopoverTrigger
      ><PopoverContent align="start" class="w-72 p-0"
        ><Command
          ><CommandInput placeholder="Найти диск…" /><CommandList
            ><CommandEmpty>Диски не найдены</CommandEmpty
            ><CommandGroup heading="Диски"
              ><CommandItem value="all" @select="emit('buckets', [])"
                ><Check v-if="!selected.length" />Все диски</CommandItem
              ><CommandItem
                v-for="bucket in buckets"
                :key="bucket.id"
                :value="bucket.id"
                :disabled="bucket.status !== 'ready'"
                :aria-disabled="bucket.status !== 'ready'"
                @select="toggle(bucket.id)"
                ><Check v-if="selected.includes(bucket.id)" /><span
                  class="min-w-0 break-all"
                  >{{ bucket.name
                  }}<span
                    v-if="bucket.status !== 'ready'"
                    class="block text-xs text-muted-foreground"
                    >{{ bucketStatusLabels[bucket.status] }}</span
                  ></span
                ><span class="sr-only">{{
                  selected.includes(bucket.id) ? "Выбран" : "Не выбран"
                }}</span></CommandItem
              ></CommandGroup
            ></CommandList
          ></Command
        ></PopoverContent
      ></Popover
    >
    <Select
      :model-value="category ?? 'all'"
      @update:model-value="
        emit(
          'category',
          $event === 'all' ? undefined : ($event as FileCategory),
        )
      "
      ><SelectTrigger aria-label="Тип файла" class="w-44"
        ><SelectValue placeholder="Все типы" /></SelectTrigger
      ><SelectContent
        ><SelectGroup
          ><SelectItem value="all">Все типы</SelectItem
          ><SelectItem
            v-for="(label, value) in categoryLabels"
            :key="value"
            :value="value"
            >{{ label }}</SelectItem
          ></SelectGroup
        ></SelectContent
      ></Select
    >
    <Button
      v-if="search || selected.length || category"
      variant="ghost"
      @click="emit('reset')"
      ><X data-icon="inline-start" />Сбросить</Button
    >
  </div>
</template>
