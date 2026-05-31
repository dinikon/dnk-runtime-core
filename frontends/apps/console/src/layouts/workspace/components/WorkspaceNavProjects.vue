<script setup lang="ts">
import { RouterLink, useRoute } from "vue-router";

import type { WorkspaceNavigationProject } from "@/app/navigation";
import {
  SidebarGroup,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";

const props = defineProps<{
  projects: WorkspaceNavigationProject[];
}>();

const route = useRoute();
</script>

<template>
  <SidebarGroup class="group-data-[collapsible=icon]:hidden">
    <SidebarGroupLabel>Projects</SidebarGroupLabel>
    <SidebarMenu>
      <SidebarMenuItem v-for="project in props.projects" :key="project.name">
        <SidebarMenuButton
          as-child
          :tooltip="project.name"
          :is-active="route.path === project.url"
        >
          <RouterLink :to="project.url">
            <component :is="project.icon" />
            <span>{{ project.name }}</span>
          </RouterLink>
        </SidebarMenuButton>
      </SidebarMenuItem>
    </SidebarMenu>
  </SidebarGroup>
</template>
