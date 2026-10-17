<script setup lang="ts">
import { ref, watch } from "vue";
import { Button } from "@/components/ui/button";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "@/components/ui/collapsible";
import { ChevronDown, FileText } from "@lucide/vue";
import ProductRichText from "../product/ProductRichText.vue";
import ProductFieldError from "../product/ProductFieldError.vue";
const props = defineProps<{
  content: Record<string, string>;
  disabled: boolean;
  error?: string;
  reveal?: number;
}>();
const emit = defineEmits<{
  change: [code: "desc" | "short_desc", value: string | undefined];
}>();
const opened = ref({ short_desc: false, desc: false });
watch(
  () => [props.error, props.reveal] as const,
  ([error, reveal], previous) => {
    if (error || (reveal && reveal !== previous?.[1]))
      opened.value = { short_desc: true, desc: true };
  },
);
</script>
<template>
  <FieldGroup class="gap-3">
    <Field
      v-for="entry in [
        { code: 'short_desc' as const, label: 'Краткое описание' },
        { code: 'desc' as const, label: 'Полное описание' },
      ]"
      :key="entry.code"
      :data-invalid="!!error || undefined"
    >
      <Collapsible v-model:open="opened[entry.code]" class="min-w-0 border-b">
        <CollapsibleTrigger
          class="group flex min-h-14 w-full items-center gap-3 py-3 text-left"
          ><FileText class="size-4 shrink-0" /><span
            class="flex min-w-0 flex-1 flex-col gap-0.5"
            ><FieldLabel as="span">{{ entry.label }}</FieldLabel
            ><span class="text-xs text-muted-foreground">{{
              content[entry.code] === undefined ? "Не добавлено" : "Добавлено"
            }}</span></span
          ><ChevronDown
            class="size-4 shrink-0 transition-transform group-data-[state=open]:rotate-180"
        /></CollapsibleTrigger>
        <CollapsibleContent
          force-mount
          v-show="opened[entry.code]"
          class="flex min-w-0 flex-col gap-3 pb-3"
        >
          <ProductRichText
            :model-value="content[entry.code] ?? ''"
            :label="entry.label"
            :disabled="disabled"
            :error-id="error ? 'descriptions-error' : undefined"
            @update:model-value="emit('change', entry.code, $event)"
          /><Button
            v-if="content[entry.code] !== undefined"
            type="button"
            variant="ghost"
            class="self-start"
            :disabled="disabled"
            @click="emit('change', entry.code, undefined)"
            >Удалить описание</Button
          >
        </CollapsibleContent>
      </Collapsible>
    </Field>
    <ProductFieldError id="descriptions-error" :error="error" />
  </FieldGroup>
</template>
