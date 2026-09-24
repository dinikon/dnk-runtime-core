<script setup lang="ts">
import {
  Check,
  ChevronsUpDown,
  Command,
  LayoutDashboard,
  Settings2,
} from "@lucide/vue";
import { RouterLink } from "vue-router";

import { useUserStore } from "@/app/stores/user";
import {
  DropdownMenu,
  DropdownMenuContent,
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
  area: "workspace" | "admin";
}>();

const userStore = useUserStore();
const { isMobile } = useSidebar();
</script>

<template>
  <SidebarMenu>
    <SidebarMenuItem>
      <DropdownMenu v-if="userStore.isAdmin">
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
            <WorkspaceTenantInfo
              :subtitle="
                area === 'admin' ? 'Администрирование' : 'Рабочее пространство'
              "
            />
            <ChevronsUpDown class="ml-auto size-4 text-muted-foreground" />
          </SidebarMenuButton>
        </DropdownMenuTrigger>
        <DropdownMenuContent
          class="min-w-60 rounded-lg"
          :side="isMobile ? 'bottom' : 'right'"
          align="start"
          :side-offset="8"
        >
          <DropdownMenuLabel class="font-normal">
            <WorkspaceTenantInfo />
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem as-child>
            <RouterLink to="/dashboard">
              <LayoutDashboard />
              <span class="flex-1">Рабочая область</span>
              <Check v-if="area === 'workspace'" class="size-4" />
            </RouterLink>
          </DropdownMenuItem>
          <DropdownMenuItem as-child>
            <RouterLink to="/admin/users">
              <Settings2 />
              <span class="flex-1">Настройки</span>
              <Check v-if="area === 'admin'" class="size-4" />
            </RouterLink>
          </DropdownMenuItem>
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
