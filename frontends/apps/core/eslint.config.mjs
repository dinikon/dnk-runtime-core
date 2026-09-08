import pluginVue from "eslint-plugin-vue";
import tseslint from "typescript-eslint";

export default [
  { ignores: [".nuxt/**", ".output/**", "dist/**", "node_modules/**"] },
  ...tseslint.configs.recommended,
  ...pluginVue.configs["flat/essential"],
  {
    files: ["**/*.{ts,vue}"],
    languageOptions: { parserOptions: { parser: tseslint.parser } },
  },
  { files: ["src/pages/**/*.vue", "src/app.vue"], rules: { "vue/multi-word-component-names": "off" } },
];
