<script setup lang="ts">
import type {Component, HTMLAttributes} from "vue"
import type {CustomButtonVariants} from "."
import {computed, useSlots} from "vue"
import {cn} from "@/lib/utils"
import {customButtonVariants} from "."

interface Props {
  variant?: CustomButtonVariants["variant"]
  accent?: CustomButtonVariants["accent"]
  size?: CustomButtonVariants["size"]
  position?: CustomButtonVariants["position"]
  fullWidth?: boolean
  inverted?: boolean
  soon?: boolean
  disabled?: boolean
  focus?: boolean
  title?: string
  type?: "button" | "submit" | "reset"
  Icon?: Component | null
  class?: HTMLAttributes["class"]
}

const props = withDefaults(defineProps<Props>(), {
  variant: "primary",
  accent: "default",
  size: "medium",
  position: "standalone",
  type: "button",
  Icon: null,
})

const slots = useSlots()

const hasDefaultSlot = computed(() => Boolean(slots.default))
const hasText = computed(() => hasDefaultSlot.value || Boolean(props.title))
</script>

<template>
  <button
      :type="type"
      :disabled="disabled"
      :aria-disabled="disabled || undefined"
      :data-variant="variant"
      :data-accent="accent"
      :data-size="size"
      :data-position="position"
      :data-inverted="inverted || undefined"
      :data-soon="soon || undefined"
      :class="cn(
        customButtonVariants({
          variant,
          accent,
          size,
          position,
          fullWidth,
          inverted,
          focus,
        }),
        props.class,
      )"
  >
    <slot name="icon">
      <component :is="Icon" v-if="Icon" aria-hidden="true"/>
    </slot>

    <span v-if="hasText" class="truncate">
      <slot>{{ title }}</slot>
    </span>

    <span
        v-if="soon"
        class="ml-0.5 rounded-[3px] bg-current/10 px-1 py-0 text-[9px] font-semibold uppercase leading-3"
    >
      Soon
    </span>
  </button>
</template>
