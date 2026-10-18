<script setup lang="ts">
import { ref, watch, useId } from "vue";
import { useEditor, EditorContent } from "@tiptap/vue-3";
import StarterKit from "@tiptap/starter-kit";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Field,
  FieldGroup,
  FieldLabel,
  FieldError,
} from "@/components/ui/field";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Bold,
  Italic,
  List,
  ListOrdered,
  Link,
  MoreHorizontal,
} from "@lucide/vue";
const props = defineProps<{
  modelValue: string;
  disabled?: boolean;
  label: string;
  errorId?: string;
  autofocus?: boolean;
}>();
const emit = defineEmits<{ "update:modelValue": [value: string] }>();
const linkOpen = ref(false);
const url = ref("");
const linkError = ref("");
const id = useId();
function attributes(): Record<string, string> {
  return {
    role: "textbox",
    "aria-label": props.label,
    "aria-multiline": "true",
    "aria-invalid": props.errorId ? "true" : "false",
    "aria-describedby": props.errorId ?? "",
    class: "product-prose min-h-36 px-4 py-3 outline-none",
  };
}
const editor = useEditor({
  content: props.modelValue,
  editable: !props.disabled,
  autofocus: props.autofocus ? "end" : false,
  extensions: [
    StarterKit.configure({
      heading: { levels: [2, 3] },
      underline: false,
      strike: false,
      horizontalRule: false,
      link: { openOnClick: false, protocols: ["http", "https", "mailto"] },
    }),
  ],
  editorProps: { attributes: attributes() },
  onUpdate: ({ editor }) => emit("update:modelValue", editor.getHTML()),
});
watch(
  () => props.disabled,
  (value) => editor.value?.setEditable(!value, false),
);
watch(
  () => props.errorId,
  () => editor.value?.setOptions({ editorProps: { attributes: attributes() } }),
);
watch(
  () => props.modelValue,
  (value) => {
    if (editor.value && value !== editor.value.getHTML())
      editor.value.commands.setContent(value, { emitUpdate: false });
  },
);
function link(): void {
  url.value = String(editor.value?.getAttributes("link").href ?? "");
  linkError.value = "";
  linkOpen.value = true;
}
function applyLink(): void {
  const value = url.value.trim();
  if (value) {
    try {
      const parsed = new URL(value);
      if (
        !["http:", "https:", "mailto:"].includes(parsed.protocol) ||
        (parsed.protocol === "mailto:" && !parsed.pathname)
      )
        throw new Error("scheme");
    } catch {
      linkError.value = "Введите адрес с https://, http:// или mailto:.";
      return;
    }
    editor.value
      ?.chain()
      .focus()
      .extendMarkRange("link")
      .setLink({ href: value })
      .run();
  } else
    editor.value?.chain().focus().extendMarkRange("link").unsetLink().run();
  linkOpen.value = false;
}
</script>
<template>
  <div
    class="min-w-0 overflow-hidden rounded-md border bg-background focus-within:ring-2 focus-within:ring-ring/40"
    :data-disabled="disabled || undefined"
  >
    <div
      v-if="editor"
      class="flex flex-wrap items-center gap-1 border-b bg-muted/30 p-1"
      role="toolbar"
      :aria-label="`Форматирование: ${label}`"
    >
      <Button
        type="button"
        variant="ghost"
        size="icon"
        aria-label="Жирный"
        :aria-pressed="editor.isActive('bold')"
        :disabled="disabled"
        @click="editor.chain().focus().toggleBold().run()"
        ><Bold
      /></Button>
      <Button
        type="button"
        variant="ghost"
        size="icon"
        aria-label="Курсив"
        :aria-pressed="editor.isActive('italic')"
        :disabled="disabled"
        @click="editor.chain().focus().toggleItalic().run()"
        ><Italic
      /></Button>
      <Button
        type="button"
        variant="ghost"
        size="icon"
        aria-label="Маркированный список"
        :aria-pressed="editor.isActive('bulletList')"
        :disabled="disabled"
        @click="editor.chain().focus().toggleBulletList().run()"
        ><List
      /></Button>
      <Button
        type="button"
        variant="ghost"
        size="icon"
        aria-label="Нумерованный список"
        :aria-pressed="editor.isActive('orderedList')"
        :disabled="disabled"
        @click="editor.chain().focus().toggleOrderedList().run()"
        ><ListOrdered
      /></Button>
      <Button
        type="button"
        variant="ghost"
        size="icon"
        aria-label="Вставить ссылку"
        :disabled="disabled"
        @click="link"
        ><Link
      /></Button>
      <DropdownMenu
        ><DropdownMenuTrigger as-child
          ><Button
            type="button"
            variant="ghost"
            size="icon"
            aria-label="Другие команды форматирования"
            :disabled="disabled"
            ><MoreHorizontal /></Button></DropdownMenuTrigger
        ><DropdownMenuContent
          ><DropdownMenuGroup>
            <DropdownMenuItem
              @select="editor.chain().focus().setParagraph().run()"
              >Абзац</DropdownMenuItem
            ><DropdownMenuItem
              @select="editor.chain().focus().toggleHeading({ level: 2 }).run()"
              >Заголовок 2</DropdownMenuItem
            ><DropdownMenuItem
              @select="editor.chain().focus().toggleHeading({ level: 3 }).run()"
              >Заголовок 3</DropdownMenuItem
            ><DropdownMenuItem
              @select="editor.chain().focus().toggleBlockquote().run()"
              >Цитата</DropdownMenuItem
            ><DropdownMenuItem
              @select="editor.chain().focus().toggleCodeBlock().run()"
              >Код</DropdownMenuItem
            ><DropdownMenuItem
              :disabled="!editor.can().undo()"
              @select="editor.chain().focus().undo().run()"
              >Отменить</DropdownMenuItem
            ><DropdownMenuItem
              :disabled="!editor.can().redo()"
              @select="editor.chain().focus().redo().run()"
              >Повторить</DropdownMenuItem
            >
          </DropdownMenuGroup></DropdownMenuContent
        ></DropdownMenu
      >
    </div>
    <EditorContent :editor="editor" />
    <Dialog v-model:open="linkOpen"
      ><DialogContent
        ><DialogHeader
          ><DialogTitle>Ссылка</DialogTitle
          ><DialogDescription
            >Укажите адрес. Пустое поле удалит ссылку из выбранного
            текста.</DialogDescription
          ></DialogHeader
        >
        <form class="flex flex-col gap-5" @submit.prevent="applyLink">
          <FieldGroup
            ><Field :data-invalid="!!linkError || undefined"
              ><FieldLabel :for="`${id}-url`">Адрес ссылки</FieldLabel
              ><Input
                :id="`${id}-url`"
                v-model="url"
                inputmode="url"
                placeholder="https://example.com"
                :aria-invalid="!!linkError || undefined"
                :aria-describedby="linkError ? `${id}-url-error` : undefined"
              /><FieldError
                v-if="linkError"
                :id="`${id}-url-error`"
                role="alert"
                >{{ linkError }}</FieldError
              ></Field
            ></FieldGroup
          ><DialogFooter
            ><Button type="button" variant="outline" @click="linkOpen = false"
              >Отмена</Button
            ><Button type="submit">Применить</Button></DialogFooter
          >
        </form></DialogContent
      ></Dialog
    >
  </div>
</template>
