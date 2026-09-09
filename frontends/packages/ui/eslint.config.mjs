import pluginVue from "eslint-plugin-vue";
import tseslint from "typescript-eslint";
export default [
  ...tseslint.configs.recommended,
  ...pluginVue.configs["flat/essential"],
  { files: ["**/*.{ts,vue}"], languageOptions: { parserOptions: { parser: tseslint.parser } } },
  { files: ["src/components/**/*.vue"], rules: { "vue/multi-word-component-names": "off" } },
];
