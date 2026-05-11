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
  <div class="grid grid-cols-6 gap-1.5" aria-label="Verification code">
    <input
        v-for="(_, index) in digits"
        :key="index"
        ref="inputs"
        :value="digits[index]"
        class="min-h-7 min-w-0 rounded border border-neutral-200 bg-white p-0 text-center text-xs text-neutral-900 outline-none transition-colors focus:border-neutral-500 focus:ring-2 focus:ring-neutral-200"
        inputmode="numeric"
        maxlength="6"
        autocomplete="one-time-code"
        @input="setDigit(index, $event)"
        @keydown="moveBack(index, $event)"
    />
  </div>
</template>
