<script setup lang="ts">
import type {HTMLAttributes} from "vue"
import {Check} from "lucide-vue-next"
import {cn} from "@/lib/utils"

const props = defineProps<{
  modelValue?: boolean
  disabled?: boolean
  class?: HTMLAttributes["class"]
}>()

const emits = defineEmits<{
  (e: "update:modelValue", payload: boolean): void
}>()
</script>

<template>
  <button
      type="button"
      role="checkbox"
      :aria-checked="modelValue"
      :disabled="disabled"
      data-slot="checkbox"
      :class="cn(
      'peer border-input dark:bg-input/30 data-[state=checked]:bg-primary data-[state=checked]:text-primary-foreground focus-visible:border-ring focus-visible:ring-ring/50 aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive size-4 shrink-0 rounded-[4px] border shadow-xs transition-shadow outline-none focus-visible:ring-[3px] disabled:cursor-not-allowed disabled:opacity-50',
      props.class,
    )"
      :data-state="modelValue ? 'checked' : 'unchecked'"
      @click="emits('update:modelValue', !modelValue)"
  >
    <Check v-if="modelValue" class="size-3.5"/>
  </button>
</template>
