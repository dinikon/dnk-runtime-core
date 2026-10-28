<script setup lang="ts">
import { RouterLink } from "vue-router";

import type { ExampleNavigationGroup } from "@/app/navigation";
import {
  SidebarGroup,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";

defineProps<{
  groups: readonly ExampleNavigationGroup[];
  activePath: string;
}>();

const emit = defineEmits<{
  navigate: [];
}>();
</script>

<template>
  <nav aria-label="Example">
    <SidebarGroup v-for="group in groups" :key="group.title">
      <SidebarGroupLabel>{{ group.title }}</SidebarGroupLabel>
      <SidebarMenu>
        <SidebarMenuItem v-for="item in group.items" :key="item.url">
          <SidebarMenuButton
            as-child
            :is-active="activePath === item.url"
            :tooltip="item.title"
          >
            <RouterLink :to="item.url" @click="emit('navigate')">
              <component :is="item.icon" />
              <span>{{ item.title }}</span>
            </RouterLink>
          </SidebarMenuButton>
        </SidebarMenuItem>
      </SidebarMenu>
    </SidebarGroup>
  </nav>
</template>
