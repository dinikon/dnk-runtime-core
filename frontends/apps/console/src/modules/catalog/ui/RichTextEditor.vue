<script setup lang="ts">
import { onBeforeUnmount, watch } from "vue";
import { EditorContent, useEditor } from "@tiptap/vue-3";
import StarterKit from "@tiptap/starter-kit";
import Link from "@tiptap/extension-link";
import { Button } from "@/components/ui/button";

const props = defineProps<{ modelValue: string; disabled?: boolean }>();
const emit = defineEmits<{ "update:modelValue": [value: string] }>();
const editor = useEditor({
  content: props.modelValue,
  editable: !props.disabled,
  extensions: [
    StarterKit.configure({ heading: { levels: [2, 3] }, link: false }),
    Link.configure({ openOnClick: false, protocols: ["https", "http"] }),
  ],
  onUpdate: ({ editor }) => emit("update:modelValue", editor.getHTML()),
});
watch(() => props.modelValue, (value) => {
  if (editor.value && editor.value.getHTML() !== value)
    editor.value.commands.setContent(value, { emitUpdate: false });
});
watch(() => props.disabled, (value) => editor.value?.setEditable(!value));
onBeforeUnmount(() => editor.value?.destroy());
function addLink() {
  const href = window.prompt("URL ссылки", "https://");
  if (href && /^https?:\/\//i.test(href))
    editor.value?.chain().focus().setLink({ href }).run();
}
</script>
<template>
  <div class="rounded-md border border-input bg-background">
    <div class="flex flex-wrap gap-1 border-b p-2">
      <Button type="button" size="sm" variant="ghost" :disabled="disabled" @click="editor?.chain().focus().toggleBold().run()">Жирный</Button>
      <Button type="button" size="sm" variant="ghost" :disabled="disabled" @click="editor?.chain().focus().toggleItalic().run()">Курсив</Button>
      <Button type="button" size="sm" variant="ghost" :disabled="disabled" @click="editor?.chain().focus().toggleBulletList().run()">Список</Button>
      <Button type="button" size="sm" variant="ghost" :disabled="disabled" @click="addLink">Ссылка</Button>
    </div>
    <EditorContent :editor="editor" class="min-h-32 px-3 py-2 text-sm [&_.tiptap]:min-h-28 [&_.tiptap]:outline-none" />
  </div>
</template>
