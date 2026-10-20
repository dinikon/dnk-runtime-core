import { test } from "node:test";
import assert from "node:assert/strict";
import { isProductImage } from "../src/modules/catalog/model/product-images.ts";

test("gallery accepts web image formats and files without a browser MIME", () => {
  for (const extension of [
    "png",
    "jpg",
    "jpeg",
    "webp",
    "gif",
    "avif",
    "bmp",
  ]) {
    assert.equal(
      isProductImage({ name: `photo.${extension}`, type: "" }),
      true,
    );
  }
  assert.equal(isProductImage({ name: "photo", type: "image/webp" }), true);
  assert.equal(
    isProductImage({ name: "photo.BMP", type: "image/x-ms-bmp" }),
    true,
  );
  assert.equal(
    isProductImage({ name: "photo.svg", type: "image/svg+xml" }),
    false,
  );
  assert.equal(
    isProductImage({ name: "document.pdf", type: "application/pdf" }),
    false,
  );
});
