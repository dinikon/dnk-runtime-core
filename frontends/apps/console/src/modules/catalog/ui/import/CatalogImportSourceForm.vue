<script setup lang="ts">
import { ref } from "vue";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Field,
  FieldGroup,
  FieldLabel,
  FieldDescription,
} from "@/components/ui/field";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
defineProps<{ pending: boolean }>();
const emit = defineEmits<{
  submit: [source: { file: File | null; url: string }];
}>();
const kind = ref("file"),
  file = ref<File | null>(null),
  url = ref("");
function selectFile(event: Event): void {
  file.value = (event.target as HTMLInputElement).files?.[0] ?? null;
}
function submit(): void {
  emit("submit", {
    file: kind.value === "file" ? file.value : null,
    url: kind.value === "url" ? url.value : "",
  });
}
</script>
<template>
  <form class="flex flex-col gap-6" @submit.prevent="submit">
    <Tabs v-model="kind">
      <TabsList aria-label="Источник импорта"
        ><TabsTrigger value="file">Файл</TabsTrigger
        ><TabsTrigger value="url">Ссылка</TabsTrigger></TabsList
      >
      <TabsContent value="file" class="pt-4">
        <FieldGroup
          ><Field
            ><FieldLabel for="import-source-file">CSV или XML</FieldLabel>
            <Input
              id="import-source-file"
              type="file"
              accept=".csv,.xml,.yml,text/csv,application/xml,text/xml"
              :disabled="pending"
              @change="selectFile"
            />
            <FieldDescription
              >Прикрепите файл экспорта. Сопоставление полей появится на
              следующем шаге.</FieldDescription
            >
          </Field></FieldGroup
        >
      </TabsContent>
      <TabsContent value="url" class="pt-4">
        <FieldGroup
          ><Field
            ><FieldLabel for="import-source-url"
              >Ссылка на CSV или XML</FieldLabel
            >
            <Input
              id="import-source-url"
              v-model="url"
              type="url"
              placeholder="https://example.com/products.xml"
              :disabled="pending"
            />
            <FieldDescription
              >Публичная ссылка без пароля. Для предпросмотра и импорта
              сохранится один снимок файла.</FieldDescription
            >
          </Field></FieldGroup
        >
      </TabsContent>
    </Tabs>
    <div class="flex justify-end">
      <Button
        type="submit"
        :disabled="pending || (kind === 'file' ? !file : !url.trim())"
        >{{ pending ? "Загрузка источника…" : "Продолжить" }}</Button
      >
    </div>
  </form>
</template>
