<script setup lang="ts">
import { computed } from "vue";
import DOMPurify from "dompurify";
import { Badge } from "@/components/ui/badge";
import type {
  RepresentationTarget,
  RepresentationFieldOrigin,
} from "../../model/representation.types";
import { representationIssueMessage } from "../../model/representation.errors";

const props = defineProps<{ target: RepresentationTarget; locale: string }>();
const content = computed(() =>
  props.target.content.find((value) => value.locale === props.locale),
);
const body = computed(() =>
  DOMPurify.sanitize(content.value?.body ?? "", {
    ALLOWED_TAGS: [
      "p",
      "br",
      "h2",
      "h3",
      "strong",
      "b",
      "em",
      "i",
      "ul",
      "ol",
      "li",
      "blockquote",
      "pre",
      "code",
      "a",
    ],
    ALLOWED_ATTR: ["href", "title"],
  }),
);
function source(value: RepresentationFieldOrigin): string {
  return value.kind === "catalog"
    ? "Из Catalog"
    : value.kind === "catalog_parent"
      ? "От родителя Catalog"
      : "Не задано";
}
</script>

<template>
  <article class="min-w-0 space-y-4 rounded-lg border p-4">
    <header class="flex flex-wrap items-center justify-between gap-2">
      <h3 class="font-medium break-words">
        {{ target.role === "container" ? "Общая карточка" : "Позиция" }} ·
        {{ target.externalId ?? "Недоступна" }}
      </h3>
      <Badge :variant="target.ready ? 'secondary' : 'outline'">{{
        target.ready ? "Контент подготовлен" : "Требует проверки"
      }}</Badge>
    </header>
    <ul
      v-if="target.issues.length"
      class="space-y-1 text-sm text-destructive"
      aria-label="Причины блокировки"
    >
      <li v-for="(issue, index) in target.issues" :key="index">
        {{ issue.locale ? `${issue.locale}: ` : ""
        }}{{ representationIssueMessage(issue.code) }}
      </li>
    </ul>
    <p v-if="!content" class="text-sm text-muted-foreground">
      Контент на выбранном языке отсутствует.
    </p>
    <dl v-else class="min-w-0 space-y-4">
      <div>
        <dt
          class="flex flex-wrap items-center justify-between gap-2 text-sm text-muted-foreground"
        >
          Название <span>{{ source(content.origins.title) }}</span>
        </dt>
        <dd class="mt-1 break-words font-medium">
          {{ content.title ?? "Не задано" }}
        </dd>
      </div>
      <div>
        <dt
          class="flex flex-wrap items-center justify-between gap-2 text-sm text-muted-foreground"
        >
          Описание <span>{{ source(content.origins.body) }}</span>
        </dt>
        <dd
          v-if="content.body === null || content.body === ''"
          class="mt-1 text-sm text-muted-foreground"
        >
          {{ content.body === null ? "Не задано" : "Пустое описание" }}
        </dd>
        <!-- HTML Catalog дополнительно очищается DOMPurify перед отображением. -->
        <!-- eslint-disable-next-line vue/no-v-html -->
        <dd
          v-else
          class="mt-2 break-words text-sm [&_ul]:list-inside [&_ul]:list-disc [&_ol]:list-inside [&_ol]:list-decimal [&_a]:underline [&_p]:my-2"
          v-html="body"
        />
      </div>
      <div>
        <dt
          class="flex flex-wrap items-center justify-between gap-2 text-sm text-muted-foreground"
        >
          Порядок изображений <span>{{ source(content.origins.gallery) }}</span>
        </dt>
        <dd
          v-if="!content.gallery?.length"
          class="mt-1 text-sm text-muted-foreground"
        >
          {{
            content.gallery === null ? "Галерея не задана" : "Пустая галерея"
          }}
        </dd>
        <dd v-else class="mt-2">
          <ol class="space-y-2">
            <li
              v-for="(image, index) in content.gallery"
              :key="`${image.fileId}-${index}`"
              class="break-words text-sm"
            >
              {{ index + 1 }}. {{ image.alt || image.caption || "Без подписи" }}
              <Badge v-if="index === 0" variant="outline">Главное</Badge>
              <p
                v-if="image.caption && image.alt"
                class="text-muted-foreground"
              >
                {{ image.caption }}
              </p>
            </li>
          </ol>
        </dd>
      </div>
    </dl>
  </article>
</template>
