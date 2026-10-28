<script setup lang="ts">
import { computed } from "vue";
import { ExternalLink, PencilLine, Rocket, Save, Share2 } from "@lucide/vue";
import { toast } from "vue-sonner";

import {
  PageHeader,
  PageHeaderActions,
  PageHeaderBreadcrumbs,
  PageHeaderSearch,
  PageHeaderTabs,
} from "@/components/custom-ui/page-header";
import type {
  PageHeaderAction,
  PageHeaderBreadcrumb,
} from "@/components/custom-ui/page-header";
import {
  headerExampleBreadcrumbs,
  headerExamples,
  headerExampleTabs,
} from "../model/header-example.constants";
import type {
  HeaderExample,
  HeaderExampleVariant,
} from "../model/header-example.types";
import { useHeaderExamplePageState } from "../model/use-header-example-page-state";
import HeaderExampleAvatar from "../ui/headers/HeaderExampleAvatar.vue";

const props = defineProps<{ variant: HeaderExampleVariant }>();
const example = computed<HeaderExample>(
  () =>
    headerExamples.find((item) => item.variant === props.variant) ??
    headerExamples[0],
);
const { activeTab, search } = useHeaderExamplePageState();
const isCompact = computed(() => props.variant === "compact");
const hasBreadcrumbs = computed(
  () => props.variant === "breadcrumbs" || props.variant === "search",
);
const hasBefore = computed(
  () =>
    hasBreadcrumbs.value ||
    props.variant === "tabs-top" ||
    props.variant === "search-avatar",
);

const actions = computed<PageHeaderAction[]>(() => {
  const primary = props.variant === "profile" ? "save" : "publish";
  const secondaryIds =
    isCompact.value || props.variant === "profile"
      ? ["view", "share", "edit"]
      : ["share", "view", "edit"];
  const definitions = {
    share: { label: "Share", icon: Share2 },
    view: { label: "View", icon: ExternalLink },
    edit: { label: "Edit", icon: PencilLine },
    publish: { label: "Publish", icon: Rocket },
    save: { label: "Save", icon: Save },
  };
  return [...secondaryIds, primary].map((id) => ({
    id,
    ...definitions[id as keyof typeof definitions],
    variant: id === primary ? "default" : isCompact.value ? "ghost" : "outline",
    mobileOrder:
      id === primary ? 1 : id === "edit" && !isCompact.value ? 2 : undefined,
  }));
});

function handleAction(action: PageHeaderAction): void {
  toast(action.label, {
    description: `Демонстрация действия ${action.label}.`,
  });
}

function handleBreadcrumb(item: PageHeaderBreadcrumb): void {
  toast(item.label, { description: `Демонстрация перехода ${item.label}.` });
}

function handleSearch(): void {
  toast("Search", {
    description: search.value.trim() || "Введите поисковый запрос.",
  });
}
</script>

<template>
  <section
    :aria-label="`Header ${example.number}`"
    class="flex min-h-0 flex-1 flex-col overflow-y-auto p-4 sm:p-6"
  >
    <PageHeader
      :title="example.title"
      :description="example.description"
      :compact="isCompact"
    >
      <template v-if="hasBefore" #before>
        <PageHeaderBreadcrumbs
          v-if="hasBreadcrumbs"
          :items="headerExampleBreadcrumbs"
          @navigate="handleBreadcrumb"
        />
        <PageHeaderTabs
          v-else-if="variant === 'tabs-top'"
          v-model="activeTab"
          :items="headerExampleTabs"
        />
        <div v-else class="flex min-w-0 items-center justify-between gap-4">
          <PageHeaderSearch
            v-model="search"
            class="w-full max-w-80"
            @submit="handleSearch"
          />
          <HeaderExampleAvatar />
        </div>
      </template>
      <template v-if="variant === 'profile'" #leading
        ><HeaderExampleAvatar
      /></template>
      <template #actions>
        <PageHeaderSearch
          v-if="variant === 'search'"
          v-model="search"
          class="w-full @2xl/page-header:w-80"
          @submit="handleSearch"
        />
        <PageHeaderActions
          v-else
          :actions="actions"
          :compact="isCompact"
          :with-icons="isCompact"
          @action="handleAction"
        />
      </template>
      <template v-if="variant === 'tabs-bottom'" #after>
        <PageHeaderTabs v-model="activeTab" :items="headerExampleTabs" />
      </template>
    </PageHeader>
  </section>
</template>
