<script setup lang="ts">
import { RouterLink, useRoute } from "vue-router";

import type { WorkspaceNavigationLink } from "@/app/navigation";
import {
  SidebarGroup,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";

const props = defineProps<{
  items: WorkspaceNavigationLink[];
}>();

const route = useRoute();
</script>

<template>
  <SidebarGroup v-bind="$attrs">
    <SidebarGroupContent>
      <SidebarMenu>
        <SidebarMenuItem v-for="item in props.items" :key="item.title">
          <SidebarMenuButton
            as-child
            size="sm"
            :tooltip="item.title"
            :is-active="route.path === item.url"
          >
            <RouterLink :to="item.url">
              <component :is="item.icon" />
              <span>{{ item.title }}</span>
            </RouterLink>
          </SidebarMenuButton>
        </SidebarMenuItem>
      </SidebarMenu>
    </SidebarGroupContent>
  </SidebarGroup>
</template>
