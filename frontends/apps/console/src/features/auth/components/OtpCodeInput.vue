<script setup lang="ts">
import {computed, nextTick, ref} from "vue";

const props = withDefaults(
    defineProps<{
      modelValue: string;
      length?: number;
    }>(),
    {
      length: 6
    }
);

const emit = defineEmits<{
  "update:modelValue": [value: string];
}>();

const inputs = ref<HTMLInputElement[]>([]);

const digits = computed(() => {
  const value = props.modelValue.replace(/\D/g, "").slice(0, props.length);
  return Array.from({length: props.length}, (_, index) => value[index] ?? "");
});

function setDigit(index: number, event: Event) {
  const input = event.target as HTMLInputElement;
  const nextDigits = [...digits.value];
  const incomingDigits = input.value.replace(/\D/g, "").slice(0, props.length).split("");

  if (incomingDigits.length > 1) {
    incomingDigits.forEach((digit, digitIndex) => {
      if (digitIndex < props.length) {
        nextDigits[digitIndex] = digit;
      }
    });
    emit("update:modelValue", nextDigits.join(""));
    void focusInput(Math.min(incomingDigits.length, props.length - 1));
    return;
  }

  nextDigits[index] = incomingDigits[0] ?? "";
  emit("update:modelValue", nextDigits.join(""));

  if (incomingDigits[0] && index < props.length - 1) {
    void focusInput(index + 1);
  }
}

function moveBack(index: number, event: KeyboardEvent) {
  if (event.key === "Backspace" && !digits.value[index] && index > 0) {
    void focusInput(index - 1);
  }
}

async function focusInput(index: number) {
  await nextTick();
  inputs.value[index]?.focus();
}
</script>

<template>
  <div class="grid grid-cols-6 gap-2" aria-label="Verification code">
    <input
        v-for="(_, index) in digits"
        :key="index"
        ref="inputs"
        :value="digits[index]"
        class="border-input bg-background focus-visible:border-ring focus-visible:ring-ring/50 h-9 min-w-0 rounded-md border p-0 text-center text-sm shadow-xs outline-none transition-[color,box-shadow] focus-visible:ring-[3px]"
        inputmode="numeric"
        maxlength="6"
        autocomplete="one-time-code"
        @input="setDigit(index, $event)"
        @keydown="moveBack(index, $event)"
    />
  </div>
</template>
