import DOMPurify from "dompurify";

const allowedMarkup = {
  ALLOWED_TAGS: ["p", "br", "strong", "em", "b", "i", "ul", "ol", "li", "blockquote", "a", "h2", "h3", "code", "pre"],
  ALLOWED_ATTR: ["href", "title", "rel"],
  ALLOW_DATA_ATTR: false,
  ALLOW_ARIA_ATTR: false,
};

export function safeRichTextHtml(value: string): string {
  return DOMPurify.sanitize(value, allowedMarkup);
}

export function richTextLength(value: string): number {
  const content = DOMPurify.sanitize(value, { ...allowedMarkup, RETURN_DOM_FRAGMENT: true });
  return Array.from(content.textContent?.trim() ?? "").length;
}
