<script setup lang="ts">
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { computed } from "vue";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
} from "@/components/ui/dropdown-menu";

const props = defineProps<{
  catalogItemId: string | null;
  pending: boolean;
  disabled: boolean;
  error: string;
  warnings: string[];
  catalogTargets?: readonly { id: string; label: string }[];
}>();
const emit = defineEmits<{
  create: [];
  connect: [];
  manage: [];
  open: [catalogItemId: string];
}>();
const targets = computed(() =>
  props.catalogTargets?.length
    ? props.catalogTargets
    : props.catalogItemId
      ? [{ id: props.catalogItemId, label: "Товар" }]
      : [],
);
const singleId = computed(() =>
  targets.value.length === 1 ? targets.value[0]!.id : null,
);
</script>

<template>
  <div class="flex min-w-0 flex-col gap-2" :aria-busy="pending">
    <Button
      class="min-h-11"
      v-if="singleId"
      variant="outline"
      :disabled="pending || disabled"
      @click="emit('open', singleId)"
    >
      Открыть товар
    </Button>
    <DropdownMenu v-else-if="targets.length > 1"
      ><DropdownMenuTrigger as-child
        ><Button
          class="min-h-11"
          type="button"
          variant="outline"
          :disabled="pending || disabled"
          >Открыть товар</Button
        ></DropdownMenuTrigger
      ><DropdownMenuContent
        ><DropdownMenuGroup
          ><DropdownMenuItem
            v-for="target in targets"
            :key="target.id"
            @select="emit('open', target.id)"
            >{{ target.label }}</DropdownMenuItem
          ></DropdownMenuGroup
        ></DropdownMenuContent
      ></DropdownMenu
    >
    <Button
      class="min-h-11"
      v-if="targets.length"
      type="button"
      variant="ghost"
      :disabled="pending || disabled"
      @click="emit('manage')"
      >Управлять связями</Button
    >
    <template v-else
      ><p class="text-sm text-muted-foreground">
        Публикация не связана с товаром.
      </p>
      <Button
        class="min-h-11"
        type="button"
        variant="outline"
        :disabled="pending || disabled"
        @click="emit('connect')"
        >Создать связь</Button
      >
      <Button
        class="min-h-11"
        type="button"
        :disabled="pending || disabled"
        @click="emit('create')"
      >
        {{ pending ? "Создание…" : "Создать товар" }}
      </Button>
      <p class="text-xs text-muted-foreground">
        Новый товар автоматически свяжется с этой публикацией.
      </p></template
    >
    <Alert v-if="error" variant="destructive" class="max-w-lg">
      <AlertDescription>{{ error }}</AlertDescription>
    </Alert>
    <Alert v-if="warnings.length" class="max-w-lg">
      <AlertDescription>
        <p v-for="warning in warnings" :key="warning">{{ warning }}</p>
      </AlertDescription>
    </Alert>
  </div>
</template>
