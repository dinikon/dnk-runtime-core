<script setup lang="ts">
import { computed } from "vue";
import {
  BadgeCheck,
  Bell,
  ChevronsUpDown,
  CreditCard,
  LogOut,
  Sparkles,
} from "@lucide/vue";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
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
import { useUserStore } from "@/app/stores/user";

const userStore = useUserStore();
const { isMobile } = useSidebar();

const displayName = computed(() => {
  const user = userStore.user;
  if (!user) {
    return userStore.primaryEmail ?? "User";
  }

  const fullName = [user.first_name, user.last_name]
    .map((part) => part.trim())
    .filter(Boolean)
    .join(" ");

  return fullName || userStore.primaryEmail || "User";
});

const primaryEmail = computed(
  () => userStore.primaryEmail ?? "No primary email",
);
const avatarUrl = computed(() => userStore.user?.avatar ?? "");
const initials = computed(() => {
  const source =
    displayName.value === "User" ? primaryEmail.value : displayName.value;
  const parts = source
    .replace(/@.*/, "")
    .split(/[\s._-]+/)
    .map((part) => part.trim())
    .filter(Boolean);

  return (
    parts
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase())
      .join("") || "U"
  );
});
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
                v-if="avatarUrl"
                :src="avatarUrl"
                :alt="displayName"
              />
              <AvatarFallback class="rounded-lg">{{ initials }}</AvatarFallback>
            </Avatar>
            <div class="grid flex-1 text-left text-sm leading-tight">
              <span class="truncate font-medium">{{ displayName }}</span>
              <span class="truncate text-xs">{{ primaryEmail }}</span>
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
              <Avatar class="h-8 w-8 rounded-lg">
                <AvatarImage
                  v-if="avatarUrl"
                  :src="avatarUrl"
                  :alt="displayName"
                />
                <AvatarFallback class="rounded-lg">{{
                  initials
                }}</AvatarFallback>
              </Avatar>
              <div class="grid flex-1 text-left text-sm leading-tight">
                <span class="truncate font-semibold">{{ displayName }}</span>
                <span class="truncate text-xs">{{ primaryEmail }}</span>
              </div>
            </div>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuGroup>
            <DropdownMenuItem>
              <Sparkles />
              Upgrade to Pro
            </DropdownMenuItem>
          </DropdownMenuGroup>
          <DropdownMenuSeparator />
          <DropdownMenuGroup>
            <DropdownMenuItem>
              <BadgeCheck />
              Account
            </DropdownMenuItem>
            <DropdownMenuItem>
              <CreditCard />
              Billing
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Bell />
              Notifications
            </DropdownMenuItem>
          </DropdownMenuGroup>
          <DropdownMenuSeparator />
          <DropdownMenuItem>
            <LogOut />
            Log out
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </SidebarMenuItem>
  </SidebarMenu>
</template>
