<script setup lang="ts">
import { computed } from "vue";
import { ChevronsUpDown, LogOut } from "lucide-vue-next";
import { useRouter } from "vue-router";

import { useSessionStore } from "@/app/stores/session";
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

const sessionStore = useSessionStore();
const logoutMutation = useLogoutMutation();
const router = useRouter();
const { isMobile } = useSidebar();

const userName = computed(() => {
  const name = [sessionStore.user?.first_name, sessionStore.user?.last_name]
    .filter(Boolean)
    .join(" ");

  return name || "Workspace user";
});

const userInitials = computed(() =>
  userName.value
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase(),
);

async function logout() {
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
            <Avatar class="size-8 rounded-lg">
              <AvatarImage
                :src="sessionStore.user?.avatar ?? undefined"
                :alt="userName"
              />
              <AvatarFallback class="rounded-lg">
                {{ userInitials }}
              </AvatarFallback>
            </Avatar>
            <div class="grid flex-1 text-left text-sm leading-tight">
              <span class="truncate font-medium">{{ userName }}</span>
              <span class="truncate text-xs">{{
                sessionStore.primaryEmail
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
          <DropdownMenuLabel class="p-0 font-normal">
            <div class="flex items-center gap-2 px-1 py-1.5 text-left text-sm">
              <Avatar class="size-8 rounded-lg">
                <AvatarImage
                  :src="sessionStore.user?.avatar ?? undefined"
                  :alt="userName"
                />
                <AvatarFallback class="rounded-lg">
                  {{ userInitials }}
                </AvatarFallback>
              </Avatar>
              <div class="grid flex-1 text-left text-sm leading-tight">
                <span class="truncate font-medium">{{ userName }}</span>
                <span class="truncate text-xs">
                  {{ sessionStore.primaryEmail }}
                </span>
              </div>
            </div>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            :disabled="logoutMutation.isPending.value"
            @select.prevent="logout"
          >
            <LogOut />
            Log out
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </SidebarMenuItem>
  </SidebarMenu>
</template>
