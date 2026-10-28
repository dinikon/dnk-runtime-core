<script setup lang="ts">
import {
  Check,
  ChevronsUpDown,
  Command,
  FlaskConical,
  LayoutDashboard,
  Settings2,
} from "@lucide/vue";
import { RouterLink } from "vue-router";

import { useUserStore } from "@/app/stores/user";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar";
import WorkspaceTenantInfo from "@/layouts/workspace/components/WorkspaceTenantInfo.vue";

defineProps<{
  area: "workspace" | "admin" | "example";
}>();

const isDev = import.meta.env.DEV;
const areaLabels = {
  workspace: "Рабочее пространство",
  admin: "Администрирование",
  example: "Example",
};
const userStore = useUserStore();
const { isMobile } = useSidebar();
</script>

<template>
  <SidebarMenu>
    <SidebarMenuItem>
      <DropdownMenu v-if="userStore.isAdmin || isDev">
        <DropdownMenuTrigger as-child>
          <SidebarMenuButton
            size="lg"
            class="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
          >
            <div
              class="flex aspect-square size-8 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground"
            >
              <Command class="size-4" />
            </div>
            <WorkspaceTenantInfo :subtitle="areaLabels[area]" />
            <ChevronsUpDown class="ml-auto size-4 text-muted-foreground" />
          </SidebarMenuButton>
        </DropdownMenuTrigger>
        <DropdownMenuContent
          class="min-w-60 rounded-lg"
          :side="isMobile ? 'bottom' : 'right'"
          align="start"
          :side-offset="8"
        >
          <DropdownMenuGroup>
            <DropdownMenuLabel class="font-normal">
              <WorkspaceTenantInfo />
            </DropdownMenuLabel>
          </DropdownMenuGroup>
          <DropdownMenuSeparator />
          <DropdownMenuGroup>
            <DropdownMenuItem as-child>
              <RouterLink to="/dashboard">
                <LayoutDashboard />
                <span class="flex-1">Рабочая область</span>
                <Check v-if="area === 'workspace'" />
              </RouterLink>
            </DropdownMenuItem>
            <DropdownMenuItem v-if="userStore.isAdmin" as-child>
              <RouterLink to="/admin/users">
                <Settings2 />
                <span class="flex-1">Настройки</span>
                <Check v-if="area === 'admin'" />
              </RouterLink>
            </DropdownMenuItem>
            <DropdownMenuItem v-if="isDev" as-child>
              <RouterLink to="/example">
                <FlaskConical />
                <span class="flex-1">Example</span>
                <Check v-if="area === 'example'" />
              </RouterLink>
            </DropdownMenuItem>
          </DropdownMenuGroup>
        </DropdownMenuContent>
      </DropdownMenu>

      <SidebarMenuButton v-else size="lg" as-child>
        <RouterLink to="/dashboard">
          <div
            class="flex aspect-square size-8 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground"
          >
            <Command class="size-4" />
          </div>
          <WorkspaceTenantInfo subtitle="Рабочее пространство" />
        </RouterLink>
      </SidebarMenuButton>
    </SidebarMenuItem>
  </SidebarMenu>
</template>
