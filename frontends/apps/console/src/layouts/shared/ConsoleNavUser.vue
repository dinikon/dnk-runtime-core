<script setup lang="ts">
import { ChevronsUpDown, LogOut, UserRound } from "@lucide/vue";
import { useRouter } from "vue-router";

import { useUserStore } from "@/app/stores/user";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
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
import { useLogoutMutation } from "@/modules/auth/mutations/use-logout";

const router = useRouter();
const userStore = useUserStore();
const logoutMutation = useLogoutMutation();
const { isMobile } = useSidebar();

async function logout() {
  if (logoutMutation.isPending.value) return;
  await logoutMutation.mutateAsync();
  await router.push({ name: "login" });
}
</script>

<template>
  <SidebarMenu>
    <SidebarMenuItem>
      <DropdownMenu>
        <DropdownMenuTrigger as-child>
          <SidebarMenuButton
            size="lg"
            class="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
          >
            <Avatar class="h-8 w-8 rounded-lg">
              <AvatarImage
                v-if="userStore.avatarUrl"
                :src="userStore.avatarUrl"
                :alt="userStore.displayName"
              />
              <AvatarFallback class="rounded-lg">{{
                userStore.initials
              }}</AvatarFallback>
            </Avatar>
            <div class="grid flex-1 text-left text-sm leading-tight">
              <span class="truncate font-medium">{{
                userStore.displayName
              }}</span>
              <span class="truncate text-xs text-muted-foreground">{{
                userStore.primaryEmail ?? "Нет основного email"
              }}</span>
            </div>
            <ChevronsUpDown class="ml-auto size-4" />
          </SidebarMenuButton>
        </DropdownMenuTrigger>
        <DropdownMenuContent
          class="w-(--reka-dropdown-menu-trigger-width) min-w-56 rounded-lg"
          :side="isMobile ? 'bottom' : 'right'"
          align="end"
          :side-offset="4"
        >
          <DropdownMenuLabel class="font-normal">
            <div class="grid text-sm leading-tight">
              <span class="truncate font-semibold">{{
                userStore.displayName
              }}</span>
              <span class="truncate text-xs text-muted-foreground">{{
                userStore.primaryEmail ?? "Нет основного email"
              }}</span>
            </div>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem as-child>
            <RouterLink to="/settings/account">
              <UserRound />
              Профиль
            </RouterLink>
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            :disabled="logoutMutation.isPending.value"
            @click="logout"
          >
            <LogOut />
            {{ logoutMutation.isPending.value ? "Выход…" : "Выйти" }}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </SidebarMenuItem>
  </SidebarMenu>
</template>
