export const productImageFormats = "PNG, JPEG, WebP, GIF, AVIF и BMP";
export const productImageAccept =
  "image/png,image/jpeg,image/webp,image/gif,image/avif,image/bmp,.png,.jpg,.jpeg,.jfif,.webp,.gif,.avif,.bmp";

export function isProductImage(file: Pick<File, "type" | "name">): boolean {
  return (
    /^(image\/(png|jpeg|jpg|webp|gif|avif|bmp|x-ms-bmp))$/.test(file.type) ||
    /\.(png|jpe?g|jfif|webp|gif|avif|bmp)$/i.test(file.name)
  );
}
