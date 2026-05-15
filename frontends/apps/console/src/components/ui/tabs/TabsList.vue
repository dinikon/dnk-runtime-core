<script setup lang="ts">
import type {TabsListProps} from "reka-ui"
import type {HTMLAttributes} from "vue"
import {reactiveOmit} from "@vueuse/core"
import {TabsList as TabsListPrimitive, useForwardProps} from "reka-ui"

import {cn} from "@/lib/utils"

interface Props extends TabsListProps {
  class?: HTMLAttributes["class"]
}

const props = defineProps<Props>()
const delegatedProps = reactiveOmit(props, "class")
const forwardedProps = useForwardProps(delegatedProps)
</script>

<template>
  <TabsListPrimitive
      data-slot="tabs-list"
      v-bind="forwardedProps"
      :class="cn('inline-flex h-10 items-start gap-1 border-b text-muted-foreground', props.class)"
  >
    <slot/>
  </TabsListPrimitive>
</template>
