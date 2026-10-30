<script setup lang="ts">
import { computed } from "vue";
import {
  Eye,
  PackageOpen,
  Unlink,
  Link2,
  PackagePlus,
  RefreshCw,
} from "@lucide/vue";
import { Button } from "@/components/ui/button";
import {
  TooltipProvider,
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
} from "@/components/ui/dropdown-menu";
const props = defineProps<{
  catalogTargets: readonly { id: string; label: string }[];
  unlinkTargets: readonly { id: string; label: string }[];
  publicationDisabled?: boolean;
  busy?: boolean;
  canConnect?: boolean;
  canSyncStock?: boolean;
}>();
const emit = defineEmits<{
  publication: [];
  stock: [];
  catalog: [id: string];
  unlink: [id: string];
  connect: [];
  create: [];
}>();
const actions = computed(() => [
  {
    kind: "catalog" as const,
    label: "Открыть товар",
    icon: PackageOpen,
    targets: props.catalogTargets,
  },
  {
    kind: "unlink" as const,
    label: "Отменить связь",
    icon: Unlink,
    targets: props.unlinkTargets,
  },
]);
function choose(kind: "catalog" | "unlink", id: string): void {
  if (kind === "catalog") emit("catalog", id);
  else emit("unlink", id);
}
</script>
<template>
  <TooltipProvider>
    <div class="flex items-center gap-1" @dblclick.stop>
      <Tooltip
        ><TooltipTrigger as-child
          ><Button
            type="button"
            variant="ghost"
            size="icon-sm"
            class="min-h-11 min-w-11 sm:min-h-8 sm:min-w-8"
            aria-label="Открыть публикацию"
            :disabled="busy || publicationDisabled"
            @click.stop="emit('publication')"
            ><Eye /></Button></TooltipTrigger
        ><TooltipContent>Открыть публикацию</TooltipContent></Tooltip
      >
      <Tooltip v-if="canSyncStock"
        ><TooltipTrigger as-child>
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            class="min-h-11 min-w-11 sm:min-h-8 sm:min-w-8"
            aria-label="Синхронизация остатков"
            :disabled="busy"
            @click.stop="emit('stock')"
            ><RefreshCw data-icon="inline-start"
          /></Button> </TooltipTrigger
        ><TooltipContent>Синхронизация остатков</TooltipContent></Tooltip
      >
      <template v-for="action in actions" :key="action.kind">
        <DropdownMenu
          v-if="
            action.kind === 'catalog' && !action.targets.length && canConnect
          "
        >
          <DropdownMenuTrigger as-child
            ><Button
              type="button"
              variant="ghost"
              size="icon-sm"
              class="min-h-11 min-w-11 sm:min-h-8 sm:min-w-8"
              aria-label="Создать связь или товар"
              title="Создать связь или товар"
              :disabled="busy"
              ><Link2 /></Button
          ></DropdownMenuTrigger>
          <DropdownMenuContent align="end"
            ><DropdownMenuGroup>
              <DropdownMenuItem @select="emit('connect')"
                ><Link2 />Создать связь</DropdownMenuItem
              >
              <DropdownMenuItem @select="emit('create')"
                ><PackagePlus />Создать товар и связать</DropdownMenuItem
              >
            </DropdownMenuGroup></DropdownMenuContent
          >
        </DropdownMenu>
        <DropdownMenu v-else-if="action.targets.length > 1">
          <DropdownMenuTrigger as-child>
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              class="min-h-11 min-w-11 sm:min-h-8 sm:min-w-8"
              :aria-label="action.label"
              :title="action.label"
              :disabled="busy"
              ><component :is="action.icon"
            /></Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end"
            ><DropdownMenuGroup
              ><DropdownMenuItem
                v-for="target in action.targets"
                :key="target.id"
                :variant="action.kind === 'unlink' ? 'destructive' : 'default'"
                @select="choose(action.kind, target.id)"
                >{{ target.label }}</DropdownMenuItem
              ></DropdownMenuGroup
            ></DropdownMenuContent
          >
        </DropdownMenu>
        <Tooltip v-else
          ><TooltipTrigger as-child
            ><Button
              type="button"
              variant="ghost"
              size="icon-sm"
              class="min-h-11 min-w-11 sm:min-h-8 sm:min-w-8"
              :aria-label="action.label"
              :disabled="busy || !action.targets.length"
              @click.stop="
                action.targets[0] && choose(action.kind, action.targets[0].id)
              "
              ><component :is="action.icon" /></Button></TooltipTrigger
          ><TooltipContent>{{
            action.targets.length
              ? action.label
              : "Публикация не связана с товаром"
          }}</TooltipContent></Tooltip
        >
      </template>
    </div>
  </TooltipProvider>
</template>
