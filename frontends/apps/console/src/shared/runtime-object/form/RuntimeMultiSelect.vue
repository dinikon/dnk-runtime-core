<script setup lang="ts">
import { computed } from "vue";
import { Check, ChevronsUpDown, X } from "@lucide/vue";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import type { RuntimeFieldOption } from "@/shared/runtime-object";

const props = withDefaults(
  defineProps<{
    modelValue?: string[];
    options: RuntimeFieldOption[];
    placeholder?: string;
  }>(),
  {
    modelValue: () => [],
    placeholder: "Select options",
  },
);

const emit = defineEmits<{
  (event: "update:modelValue", value: string[]): void;
}>();

const selectedValues = computed(() => new Set(props.modelValue));
const selectedOptions = computed(() =>
  props.options.filter((option) => selectedValues.value.has(option.value)),
);

function toggleOption(value: string) {
  const next = new Set(props.modelValue);

  if (next.has(value)) {
    next.delete(value);
  } else {
    next.add(value);
  }

  emit("update:modelValue", Array.from(next));
}

function removeOption(value: string) {
  emit(
    "update:modelValue",
    props.modelValue.filter((item) => item !== value),
  );
}
</script>

<template>
  <div class="grid gap-2">
    <Popover>
      <PopoverTrigger as-child>
        <Button
          type="button"
          variant="outline"
          class="h-auto min-h-9 justify-between px-3 font-normal"
        >
          <span class="truncate text-muted-foreground">
            {{
              selectedOptions.length
                ? `${selectedOptions.length} selected`
                : placeholder
            }}
          </span>
          <ChevronsUpDown class="ml-2 size-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent class="w-72 p-0" align="start">
        <Command>
          <CommandInput placeholder="Search options..." />
          <CommandList>
            <CommandEmpty>No options found.</CommandEmpty>
            <CommandGroup>
              <CommandItem
                v-for="option in options"
                :key="option.value"
                :value="option.label"
                @select="toggleOption(option.value)"
              >
                <Checkbox
                  :model-value="selectedValues.has(option.value)"
                  class="pointer-events-none"
                />
                <span>{{ option.label }}</span>
                <Check
                  v-if="selectedValues.has(option.value)"
                  class="ml-auto size-4"
                />
              </CommandItem>
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>

    <div v-if="selectedOptions.length" class="flex flex-wrap gap-1.5">
      <Badge
        v-for="option in selectedOptions"
        :key="option.value"
        variant="secondary"
        class="gap-1"
      >
        {{ option.label }}
        <button
          type="button"
          class="rounded-sm opacity-70 hover:opacity-100"
          @click="removeOption(option.value)"
        >
          <X class="size-3" />
          <span class="sr-only">Remove {{ option.label }}</span>
        </button>
      </Badge>
    </div>
  </div>
</template>
