// Service: a quick check before uploading a logo (Q16). The server checks the bytes themselves
// and re-encodes the image; this only saves a pointless upload.

export const MAX_LOGO_BYTES = 1_000_000;

export function logoProblem(file: { type: string; size: number }): string | null {
  if (!["image/png", "image/jpeg"].includes(file.type)) return "Choose a PNG or JPEG image.";
  if (file.size > MAX_LOGO_BYTES) return "The logo can be at most 1 MB.";
  return null;
}

/** Base64 of the file's bytes (what the API expects), without the "data:...," prefix. */
export function base64FromDataUrl(dataUrl: string): string {
  const comma = dataUrl.indexOf(",");
  return comma === -1 ? "" : dataUrl.slice(comma + 1);
}
