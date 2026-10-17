<script setup lang="ts">
import { watch } from "vue";
import { useEditor, EditorContent } from "@tiptap/vue-3";
import StarterKit from "@tiptap/starter-kit";
import { Button } from "@/components/ui/button";
import {
  Bold,
  Italic,
  List,
  ListOrdered,
  Quote,
  Code,
  Link,
  Undo2,
  Redo2,
} from "@lucide/vue";
const props = defineProps<{
  modelValue: string;
  disabled?: boolean;
  label: string;
}>();
const emit = defineEmits<{ "update:modelValue": [value: string] }>();
const editor = useEditor({
  content: props.modelValue,
  editable: !props.disabled,
  extensions: [
    StarterKit.configure({
      heading: { levels: [2, 3] },
      underline: false,
      strike: false,
      horizontalRule: false,
      link: { openOnClick: false, protocols: ["http", "https", "mailto"] },
    }),
  ],
  editorProps: {
    attributes: {
      role: "textbox",
      "aria-label": props.label,
      "aria-multiline": "true",
      class: "product-prose min-h-36 px-4 py-3 outline-none",
    },
  },
  onUpdate: ({ editor }) => {
    emit("update:modelValue", editor.getHTML());
  },
});
watch(
  () => props.disabled,
  (v) => editor.value?.setEditable(!v, false),
);
watch(
  () => props.modelValue,
  (v) => {
    if (editor.value && v !== editor.value.getHTML())
      editor.value.commands.setContent(v, { emitUpdate: false });
  },
);
function link() {
  const url = window.prompt(
    "Адрес ссылки (https://, http:// или mailto:)",
    String(editor.value?.getAttributes("link").href ?? ""),
  );
  if (url === null) return;
  if (!url)
    editor.value?.chain().focus().extendMarkRange("link").unsetLink().run();
  else if (/^(https?:\/\/|mailto:)/i.test(url))
    editor.value
      ?.chain()
      .focus()
      .extendMarkRange("link")
      .setLink({ href: url })
      .run();
}
</script>
<template>
  <div
    class="overflow-hidden rounded-md border bg-background"
    :data-disabled="disabled || undefined"
  >
    <div
      v-if="editor"
      class="flex flex-wrap items-center gap-1 border-b bg-muted/30 p-1"
      role="toolbar"
      :aria-label="`Форматирование: ${label}`"
    >
      <select
        aria-label="Формат текста"
        :disabled="disabled"
        class="rounded bg-transparent px-2 py-1 text-sm"
        :value="
          editor.isActive('heading', { level: 2 })
            ? '2'
            : editor.isActive('heading', { level: 3 })
              ? '3'
              : 'p'
        "
        @change="
          ($event.target as HTMLSelectElement).value === 'p'
            ? editor.chain().focus().setParagraph().run()
            : editor
                .chain()
                .focus()
                .setHeading({
                  level: Number(($event.target as HTMLSelectElement).value) as
                    2 | 3,
                })
                .run()
        "
      >
        <option value="p">Абзац</option>
        <option value="2">Заголовок 2</option>
        <option value="3">Заголовок 3</option>
      </select>
      <Button
        type="button"
        variant="ghost"
        size="icon-sm"
        aria-label="Жирный"
        :aria-pressed="editor.isActive('bold')"
        :disabled="disabled"
        @click="editor.chain().focus().toggleBold().run()"
        ><Bold
      /></Button>
      <Button
        type="button"
        variant="ghost"
        size="icon-sm"
        aria-label="Курсив"
        :aria-pressed="editor.isActive('italic')"
        :disabled="disabled"
        @click="editor.chain().focus().toggleItalic().run()"
        ><Italic
      /></Button>
      <Button
        type="button"
        variant="ghost"
        size="icon-sm"
        aria-label="Список"
        :aria-pressed="editor.isActive('bulletList')"
        :disabled="disabled"
        @click="editor.chain().focus().toggleBulletList().run()"
        ><List
      /></Button>
      <Button
        type="button"
        variant="ghost"
        size="icon-sm"
        aria-label="Нумерованный список"
        :aria-pressed="editor.isActive('orderedList')"
        :disabled="disabled"
        @click="editor.chain().focus().toggleOrderedList().run()"
        ><ListOrdered
      /></Button>
      <Button
        type="button"
        variant="ghost"
        size="icon-sm"
        aria-label="Цитата"
        :aria-pressed="editor.isActive('blockquote')"
        :disabled="disabled"
        @click="editor.chain().focus().toggleBlockquote().run()"
        ><Quote
      /></Button>
      <Button
        type="button"
        variant="ghost"
        size="icon-sm"
        aria-label="Код"
        :aria-pressed="editor.isActive('code')"
        :disabled="disabled"
        @click="editor.chain().focus().toggleCode().run()"
        ><Code
      /></Button>
      <Button
        type="button"
        variant="ghost"
        size="icon-sm"
        aria-label="Ссылка"
        :disabled="disabled"
        @click="link"
        ><Link
      /></Button>
      <Button
        type="button"
        variant="ghost"
        size="icon-sm"
        aria-label="Отменить форматирование"
        :disabled="disabled || !editor.can().undo()"
        @click="editor.chain().focus().undo().run()"
        ><Undo2
      /></Button>
      <Button
        type="button"
        variant="ghost"
        size="icon-sm"
        aria-label="Повторить форматирование"
        :disabled="disabled || !editor.can().redo()"
        @click="editor.chain().focus().redo().run()"
        ><Redo2
      /></Button>
    </div>
    <EditorContent :editor="editor" />
  </div>
</template>
