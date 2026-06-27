<script setup lang="ts">
import type { WorkspaceNavigationItem } from "@/app/navigation";
import { RouterLink } from "vue-router";

import {
  SidebarGroup,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";

defineProps<{
  items: WorkspaceNavigationItem[];
}>();
</script>

<template>
  <SidebarGroup>
    <SidebarGroupContent>
      <SidebarMenu>
        <SidebarMenuItem v-for="item in items" :key="item.title">
          <SidebarMenuButton as-child size="sm">
            <a
              v-if="item.external"
              :href="item.url"
              target="_blank"
              rel="noopener noreferrer"
            >
              <component :is="item.icon" />
              <span>{{ item.title }}</span>
            </a>
            <RouterLink v-else :to="item.url">
              <component :is="item.icon" />
              <span>{{ item.title }}</span>
            </RouterLink>
          </SidebarMenuButton>
        </SidebarMenuItem>
      </SidebarMenu>
    </SidebarGroupContent>
  </SidebarGroup>
</template>
