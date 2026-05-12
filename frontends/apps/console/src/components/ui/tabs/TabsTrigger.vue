<script setup lang="ts">
import type {TabsTriggerProps} from "reka-ui"
import type {HTMLAttributes} from "vue"
import {reactiveOmit} from "@vueuse/core"
import {TabsTrigger as TabsTriggerPrimitive, useForwardProps} from "reka-ui"

import {cn} from "@/lib/utils"

interface Props extends TabsTriggerProps {
  class?: HTMLAttributes["class"]
}

const props = defineProps<Props>()
const delegatedProps = reactiveOmit(props, "class")
const forwardedProps = useForwardProps(delegatedProps)
</script>

<template>
  <TabsTriggerPrimitive
      data-slot="tabs-trigger"
      v-bind="forwardedProps"
      :class="cn(
      'inline-flex h-10 items-center justify-center gap-1.5 border-b border-transparent px-2 text-sm font-medium whitespace-nowrap transition-colors outline-none hover:text-foreground focus-visible:ring-ring/50 focus-visible:ring-[3px] disabled:pointer-events-none disabled:opacity-50 data-[state=active]:border-foreground data-[state=active]:text-foreground [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0',
      props.class,
    )"
  >
    <slot/>
  </TabsTriggerPrimitive>
</template>
