<script setup lang="ts">
import {
  AtSign,
  BadgeDollarSign,
  Bell,
  Boxes,
  CalendarDays,
  Code2,
  Database,
  Globe2,
  HelpCircle,
  KeyRound,
  LockKeyhole,
  LogOut,
  Mail,
  MonitorCog,
  Rocket,
  Server,
  Settings,
  Sparkles,
  UserCircle,
  Users,
  X
} from "lucide-vue-next";
import {RouterLink} from "vue-router";

interface BreadcrumbItem {
  label: string;
  to?: string;
}

defineProps<{
  title: string;
  breadcrumbs: BreadcrumbItem[];
  activeItem: string;
}>();

const userItems = [
  {id: "profile", label: "Profile", to: "/settings/profile", icon: UserCircle},
  {id: "experience", label: "Experience", to: "/settings/experience", icon: MonitorCog},
  {id: "accounts", label: "Accounts", to: "/settings/accounts", icon: AtSign},
  {id: "emails", label: "Emails", to: "/settings/accounts/emails", icon: Mail, nested: true},
  {id: "calendar", label: "Calendar", to: "/settings/accounts/calendar", icon: CalendarDays, nested: true}
];

const workspaceItems = [
  {id: "workspace-general", label: "General", to: "/settings/workspace/general", icon: Settings},
  {id: "data-model", label: "Data Model", to: "/settings/workspace/data-model", icon: Database},
  {id: "members", label: "Members", to: "/settings/workspace/members", icon: Users},
  {id: "roles", label: "Roles", to: "/settings/workspace/roles", icon: LockKeyhole},
  {id: "domains", label: "Domains", to: "/settings/workspace/domains", icon: Globe2},
  {id: "billing", label: "Billing", to: "/settings/workspace/billing", icon: BadgeDollarSign},
  {id: "apis-webhooks", label: "APIs & Webhooks", to: "/settings/workspace/apis-webhooks", icon: Code2},
  {id: "apps", label: "Apps", to: "/settings/workspace/apps", icon: Boxes},
  {id: "ai", label: "AI", to: "/settings/workspace/ai", icon: Sparkles},
  {id: "security", label: "Security", to: "/settings/workspace/security", icon: KeyRound}
];

const otherItems = [
  {id: "admin-panel", label: "Admin Panel", to: "/settings/admin-panel", icon: Server},
  {id: "updates", label: "Updates", to: "/settings/updates", icon: Rocket},
  {id: "support", label: "Support", to: "/settings/support", icon: Bell},
  {id: "documentation", label: "Documentation", to: "/settings/documentation", icon: HelpCircle},
  {id: "logout", label: "Log out", to: "/login", icon: LogOut}
];
</script>

<template>
  <div class="flex h-screen overflow-hidden bg-neutral-100 text-neutral-900">
    <aside class="flex h-screen w-[320px] shrink-0 flex-col px-7 py-7">
      <RouterLink
          class="mb-9 inline-flex min-h-8 items-center gap-2 text-sm font-semibold text-neutral-600 hover:text-neutral-900"
          to="/"
      >
        <X class="size-4"/>
        Exit Settings
      </RouterLink>

      <nav class="min-h-0 flex-1 overflow-y-auto pr-2">
        <section class="grid gap-1">
          <h2 class="mb-1 px-1 text-xs font-semibold text-neutral-400">User</h2>
          <RouterLink
              v-for="item in userItems"
              :key="item.id"
              class="flex min-h-9 items-center gap-2 rounded-md px-2 text-sm font-medium text-neutral-600 transition-colors hover:bg-neutral-200/60 hover:text-neutral-900"
              :class="[
              activeItem === item.id ? 'bg-neutral-200/80 text-neutral-900' : '',
              item.nested ? 'ml-4 border-l border-neutral-200 pl-4' : ''
            ]"
              :to="item.to"
          >
            <component :is="item.icon" class="size-4"/>
            <span class="truncate">{{ item.label }}</span>
          </RouterLink>
        </section>

        <section class="mt-6 grid gap-1">
          <h2 class="mb-1 px-1 text-xs font-semibold text-neutral-400">Workspace</h2>
          <RouterLink
              v-for="item in workspaceItems"
              :key="item.id"
              class="flex min-h-9 items-center gap-2 rounded-md px-2 text-sm font-medium text-neutral-600 transition-colors hover:bg-neutral-200/60 hover:text-neutral-900"
              :class="activeItem === item.id ? 'bg-neutral-200/80 text-neutral-900' : ''"
              :to="item.to"
          >
            <component :is="item.icon" class="size-4"/>
            <span class="truncate">{{ item.label }}</span>
          </RouterLink>
        </section>

        <section class="mt-6 grid gap-1">
          <h2 class="mb-1 px-1 text-xs font-semibold text-neutral-400">Other</h2>
          <RouterLink
              v-for="item in otherItems"
              :key="item.id"
              class="flex min-h-9 items-center gap-2 rounded-md px-2 text-sm font-medium text-neutral-600 transition-colors hover:bg-neutral-200/60 hover:text-neutral-900"
              :class="activeItem === item.id ? 'bg-neutral-200/80 text-neutral-900' : ''"
              :to="item.to"
          >
            <component :is="item.icon" class="size-4"/>
            <span class="truncate">{{ item.label }}</span>
          </RouterLink>
        </section>
      </nav>

      <div class="mt-5 flex items-center justify-between gap-3 px-1">
        <span class="inline-flex items-center gap-3 text-sm font-medium text-neutral-600">
          <span class="size-1.5 rounded-full bg-yellow-400"/>
          Advanced:
        </span>
        <span class="relative inline-flex h-6 w-11 items-center rounded-full bg-yellow-400">
          <span class="absolute right-0.5 size-5 rounded-full bg-white shadow-sm"/>
        </span>
      </div>
    </aside>

    <main class="flex min-w-0 flex-1 flex-col gap-6 px-6 py-7">
      <header class="flex min-h-8 items-center gap-2 text-sm font-medium text-neutral-400">
        <template v-for="(breadcrumb, index) in breadcrumbs" :key="`${breadcrumb.label}-${index}`">
          <RouterLink
              v-if="breadcrumb.to"
              class="hover:text-neutral-800"
              :to="breadcrumb.to"
          >
            {{ breadcrumb.label }}
          </RouterLink>
          <span v-else :class="index === breadcrumbs.length - 1 ? 'text-neutral-800' : ''">
            {{ breadcrumb.label }}
          </span>
          <span v-if="index < breadcrumbs.length - 1" class="text-neutral-500">/</span>
        </template>
      </header>

      <section class="min-h-0 flex-1 overflow-auto rounded-lg border border-neutral-200 bg-white px-8 py-8 shadow-sm">
        <slot>
          <div class="text-sm text-neutral-400">{{ title }}</div>
        </slot>
      </section>
    </main>
  </div>
</template>
