<script setup lang="ts">
import type {TabsContentProps} from "reka-ui"
import type {HTMLAttributes} from "vue"
import {reactiveOmit} from "@vueuse/core"
import {TabsContent as TabsContentPrimitive, useForwardProps} from "reka-ui"

import {cn} from "@/lib/utils"

interface Props extends TabsContentProps {
  class?: HTMLAttributes["class"]
}

const props = defineProps<Props>()
const delegatedProps = reactiveOmit(props, "class")
const forwardedProps = useForwardProps(delegatedProps)
</script>

<template>
  <TabsContentPrimitive
      data-slot="tabs-content"
      v-bind="forwardedProps"
      :class="cn('outline-none', props.class)"
  >
    <slot/>
  </TabsContentPrimitive>
</template>
