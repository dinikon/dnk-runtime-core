<script setup lang="ts">
import { Background } from "@vue-flow/background";
import { VueFlow, type Edge, type Node } from "@vue-flow/core";

import "@vue-flow/core/dist/style.css";
import "@vue-flow/core/dist/theme-default.css";

const nodes: Node[] = [];
const edges: Edge[] = [];
</script>

<template>
  <VueFlow
    :nodes="nodes"
    :edges="edges"
    :nodes-draggable="false"
    :nodes-connectable="false"
    :elements-selectable="false"
    :pan-on-drag="true"
    :zoom-on-scroll="true"
    :zoom-on-pinch="true"
    :prevent-scrolling="true"
    class="h-full w-full bg-background"
  >
    <Background
      variant="dots"
      color="var(--border)"
      :gap="24"
      :size="1.5"
    />
  </VueFlow>
</template>
