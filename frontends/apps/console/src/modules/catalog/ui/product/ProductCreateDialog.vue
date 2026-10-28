<script setup lang="ts">
import "./product.css";
import { nextTick, watch } from "vue";
import { useMediaQuery } from "@vueuse/core";
import { Package, Sparkles, ArrowRight, LoaderCircle } from "@lucide/vue";
import { Button } from "@/components/ui/button";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  Drawer,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
  DrawerDescription,
} from "@/components/ui/drawer";
import type {
  ProductCreationState,
  ProductPreset,
} from "../../model/product-creation";
const props = defineProps<{
  open: boolean;
  state: ProductCreationState;
  disabled: boolean;
}>();
const emit = defineEmits<{
  close: [];
  choose: [preset: ProductPreset];
  check: [];
}>();
const desktop = useMediaQuery("(min-width: 640px)");
let opener: HTMLElement | null = null;
watch(
  () => props.open,
  (open) => {
    if (open) opener = document.activeElement as HTMLElement | null;
  },
  { immediate: true },
);
async function focusOptions(event: Event): Promise<void> {
  event.preventDefault();
  const panel = event.target as HTMLElement;
  await nextTick();
  panel
    .querySelector<HTMLButtonElement>("button:not(:disabled)")
    ?.focus({ preventScroll: true });
}
function restoreFocus(event: Event): void {
  if (opener?.isConnected) {
    event.preventDefault();
    opener.focus();
  }
}
function preventWhilePending(event: Event): void {
  if (props.state.pending) event.preventDefault();
}
</script>

<template>
  <component
    :is="desktop ? Dialog : Drawer"
    :open="open"
    :dismissible="!state.pending"
    @update:open="!$event && emit('close')"
  >
    <component
      :is="desktop ? DialogContent : DrawerContent"
      :show-close-button="false"
      class="product-create-dialog"
      @escape-key-down="preventWhilePending"
      @interact-outside="preventWhilePending"
      @open-auto-focus="focusOptions"
      @close-auto-focus="restoreFocus"
    >
      <component
        :is="desktop ? DialogHeader : DrawerHeader"
        class="p-0 text-left"
      >
        <component :is="desktop ? DialogTitle : DrawerTitle"
          >Создать товар</component
        >
        <component :is="desktop ? DialogDescription : DrawerDescription"
          >Выберите, с какой карточки начать. Тип карточки выбирается при
          создании.</component
        >
      </component>
      <div class="flex flex-col gap-3" :aria-busy="state.pending">
        <Button
          v-for="option in [
            {
              id: 'simple' as const,
              title: 'Простой товар',
              text: 'Обычная карточка. Виртуальный товар выключен.',
              icon: Package,
            },
            {
              id: 'variable' as const,
              title: 'Вариативный товар',
              text: 'Общая карточка с отдельными продаваемыми вариантами.',
              icon: Package,
            },
            {
              id: 'service' as const,
              title: 'Услуга',
              text: 'Та же карточка. Виртуальный товар включён.',
              icon: Sparkles,
            },
          ]"
          :key="option.id"
          variant="outline"
          class="h-auto min-h-24 w-full justify-start gap-4 whitespace-normal p-4 text-left"
          :disabled="
            disabled || state.pending || state.uncertain || !!state.createdId
          "
          @click="emit('choose', option.id)"
        >
          <component
            :is="
              state.pending && state.preset === option.id
                ? LoaderCircle
                : option.icon
            "
            data-icon="inline-start"
            :class="{
              'animate-spin': state.pending && state.preset === option.id,
            }"
          />
          <span class="flex min-w-0 flex-1 flex-col gap-1"
            ><span class="font-semibold">{{
              state.pending && state.preset === option.id
                ? "Создание…"
                : option.title
            }}</span
            ><span class="text-sm font-normal text-muted-foreground">{{
              option.text
            }}</span></span
          >
          <ArrowRight data-icon="inline-end" />
        </Button>
        <p v-if="disabled" class="text-sm text-muted-foreground">
          Создание доступно после выбора активного языка каталога.
        </p>
        <Alert v-if="state.error" variant="destructive"
          ><AlertTitle>{{
            state.createdId ? "Товар создан" : "Не удалось завершить создание"
          }}</AlertTitle
          ><AlertDescription>{{ state.error }}</AlertDescription></Alert
        >
        <Button
          v-if="state.createdId"
          :disabled="state.pending"
          class="min-h-11"
          @click="emit('choose', state.preset ?? 'simple')"
          >Открыть созданный товар</Button
        >
        <Button
          v-if="state.uncertain"
          variant="outline"
          class="min-h-11"
          @click="emit('check')"
          >Проверить каталог</Button
        >
        <Button
          variant="ghost"
          class="min-h-11"
          :disabled="state.pending"
          @click="emit('close')"
          >Отмена</Button
        >
      </div>
    </component>
  </component>
</template>
