/** Десятичная клавиатура locale может вводить запятую; API получает строку с точкой. */
export function decimalInput(value: string | number): string {
  return String(value).replace(",", ".");
}
