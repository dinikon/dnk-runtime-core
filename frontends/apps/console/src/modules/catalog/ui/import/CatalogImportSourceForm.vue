<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { Upload, FileText, X } from "@lucide/vue";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Field,
  FieldGroup,
  FieldLabel,
  FieldDescription,
} from "@/components/ui/field";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
const props = defineProps<{ pending: boolean; formId: string }>();
const emit = defineEmits<{
  submit: [source: { file: File | null; url: string }];
  ready: [value: boolean];
}>();
const kind = ref("file"),
  file = ref<File | null>(null),
  url = ref(""),
  fileKey = ref(0),
  dragging = ref(false);
const ready = computed(() =>
  kind.value === "file" ? !!file.value : !!url.value.trim(),
);
watch(ready, (value) => emit("ready", value), { immediate: true });
function selectFile(event: Event): void {
  file.value = (event.target as HTMLInputElement).files?.[0] ?? null;
}
function drop(event: DragEvent): void {
  dragging.value = false;
  if (!props.pending) file.value = event.dataTransfer?.files[0] ?? null;
}
function remove(): void {
  file.value = null;
  fileKey.value++;
}
function submit(): void {
  if (!ready.value || props.pending) return;
  emit("submit", {
    file: kind.value === "file" ? file.value : null,
    url: kind.value === "url" ? url.value : "",
  });
}
</script>
<template>
  <form
    :id="formId"
    class="mx-auto flex w-full max-w-xl flex-col gap-6 py-2 sm:py-5"
    @submit.prevent="submit"
  >
    <div class="flex flex-col gap-2">
      <h3 class="text-xl font-semibold tracking-tight">Выберите источник</h3>
      <p class="text-sm leading-relaxed text-muted-foreground">
        Загрузите файл с товарами в формате CSV или XML либо укажите ссылку на
        файл.
      </p>
    </div>
    <Tabs v-model="kind" class="gap-5">
      <TabsList
        class="grid h-11 w-full grid-cols-2"
        aria-label="Источник импорта"
      >
        <TabsTrigger value="file" :disabled="pending">Файл</TabsTrigger>
        <TabsTrigger value="url" :disabled="pending">Ссылка</TabsTrigger>
      </TabsList>
      <TabsContent value="file">
        <FieldGroup>
          <Field>
            <div
              class="group"
              @dragover.prevent="dragging = true"
              @dragleave.prevent="dragging = false"
              @drop.prevent="drop"
            >
              <FieldLabel
                for="import-source-file"
                :data-dragging="dragging"
                class="flex min-h-48 cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border border-dashed bg-muted/30 p-6 text-center transition-colors hover:bg-muted/60 group-focus-within:ring-2 group-focus-within:ring-ring data-[dragging=true]:bg-muted sm:min-h-60"
              >
                <Upload
                  class="size-8 text-muted-foreground"
                  aria-hidden="true"
                />
                <span>Выберите CSV или XML</span>
                <span class="text-sm font-normal text-muted-foreground"
                  >До 100 МБ · можно перетащить сюда</span
                >
              </FieldLabel>
              <Input
                :key="fileKey"
                id="import-source-file"
                type="file"
                class="sr-only"
                accept=".csv,.xml,.yml,text/csv,application/xml,text/xml"
                :disabled="pending"
                @change="selectFile"
              />
            </div>
            <FieldDescription
              >Сопоставление полей появится на следующем шаге.</FieldDescription
            >
          </Field>
        </FieldGroup>
        <div
          v-if="file"
          class="mt-5 flex min-w-0 items-center gap-3 rounded-lg border bg-muted/30 p-3"
        >
          <FileText
            class="size-6 shrink-0 text-muted-foreground"
            aria-hidden="true"
          />
          <div class="min-w-0 flex-1">
            <p class="truncate text-sm font-medium" :title="file.name">
              {{ file.name }}
            </p>
            <p class="text-xs text-muted-foreground">
              {{
                (file.size / 1024).toLocaleString("ru", {
                  maximumFractionDigits: 1,
                })
              }}
              КБ
            </p>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            class="size-11 shrink-0"
            aria-label="Убрать файл"
            :disabled="pending"
            @click="remove"
            ><X
          /></Button>
        </div>
      </TabsContent>
      <TabsContent value="url">
        <FieldGroup
          ><Field
            ><FieldLabel for="import-source-url"
              >Ссылка на CSV или XML</FieldLabel
            >
            <Input
              id="import-source-url"
              v-model="url"
              class="h-11"
              type="url"
              inputmode="url"
              autocomplete="url"
              placeholder="https://example.com/products.xml"
              :disabled="pending"
            />
            <FieldDescription
              >Публичная ссылка без пароля. Предпросмотр и импорт используют
              один сохранённый снимок файла.</FieldDescription
            >
          </Field></FieldGroup
        >
      </TabsContent>
    </Tabs>
  </form>
</template>
