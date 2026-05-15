<script setup lang="ts">
import type {TabsRootEmits, TabsRootProps} from "reka-ui"
import {TabsRoot as TabsRootPrimitive, useForwardPropsEmits} from "reka-ui"

const props = defineProps<TabsRootProps>()
const emits = defineEmits<TabsRootEmits>()

const forwarded = useForwardPropsEmits(props, emits)
</script>

<template>
  <TabsRootPrimitive
      data-slot="tabs"
      v-bind="forwarded"
  >
    <slot/>
  </TabsRootPrimitive>
</template>
