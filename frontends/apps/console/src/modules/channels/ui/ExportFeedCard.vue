<script setup lang="ts">
import { ref, watch } from "vue";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Field,
  FieldGroup,
  FieldLabel,
  FieldDescription,
} from "@/components/ui/field";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  CardDescription,
} from "@/components/ui/card";
import { dateLabel } from "../model/channels.presentation";

const props = defineProps<{
  url: string;
  expiresAt: string;
  fileOnly: boolean;
}>();
const copying = ref(false),
  copied = ref(false),
  error = ref(false);
watch(
  () => props.url,
  () => {
    copied.value = false;
    error.value = false;
  },
);
async function copy(): Promise<void> {
  if (copying.value) return;
  const value = props.url;
  copying.value = true;
  error.value = false;
  try {
    await navigator.clipboard.writeText(value);
    if (props.url === value) copied.value = true;
  } catch {
    if (props.url === value) error.value = true;
  } finally {
    copying.value = false;
  }
}
</script>
<template>
  <Card>
    <CardHeader>
      <CardTitle>Ссылка на XML</CardTitle>
      <CardDescription>{{
        fileOnly
          ? "Файл сформирован. Отправка в источник не выполнялась."
          : "Эта ссылка передаётся источнику для загрузки подготовленного файла."
      }}</CardDescription>
    </CardHeader>
    <CardContent class="flex flex-col gap-3">
      <FieldGroup
        ><Field>
          <FieldLabel for="export-feed-url">Адрес выгрузки</FieldLabel>
          <Input
            id="export-feed-url"
            :model-value="url"
            readonly
            @focus="($event.target as HTMLInputElement).select()"
          />
          <FieldDescription
            >Снимок текущего запуска. Доступен до {{ dateLabel(expiresAt) }}.
            Ссылка открывает файл без входа в Console; передавайте её только
            доверенному получателю.</FieldDescription
          >
        </Field></FieldGroup
      >
      <div class="flex flex-wrap gap-2">
        <Button variant="outline" :disabled="copying" @click="copy">{{
          copied
            ? "Ссылка скопирована"
            : copying
              ? "Копируем…"
              : "Скопировать ссылку"
        }}</Button>
        <Button variant="outline" as-child
          ><a
            :href="url"
            target="_blank"
            rel="noopener noreferrer"
            referrerpolicy="no-referrer"
            >Открыть XML</a
          ></Button
        >
      </div>
      <p v-if="fileOnly" class="text-muted-foreground text-sm">
        При ручном импорте выберите обновление названий и описаний на двух
        языках. Остальные поля и отсутствующие в файле товары оставьте без
        изменений.
      </p>
      <p v-if="error" role="status" class="text-destructive text-sm">
        Не удалось скопировать. Выделите адрес в поле и скопируйте вручную.
      </p>
      <p v-else-if="copied" role="status" class="text-muted-foreground text-sm">
        Ссылка скопирована в буфер обмена.
      </p>
    </CardContent>
  </Card>
</template>
