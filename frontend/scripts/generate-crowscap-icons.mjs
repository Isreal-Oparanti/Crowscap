import path from "node:path";
import { fileURLToPath } from "node:url";

import sharp from "sharp";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(__dirname, "..");
const input =
  process.argv[2] ??
  "C:/Users/USER/AppData/Local/Temp/codex-clipboard-ecef0be0-21b1-4566-8670-3fac954a27cd.png";
const outputDir = path.join(frontendRoot, "public", "icons");

async function saveIcon(size, fileName, padding) {
  await sharp(input)
    .trim({ background: "#ffffff", threshold: 8 })
    .resize({
      width: size - padding * 2,
      height: size - padding * 2,
      fit: "inside",
      withoutEnlargement: false,
    })
    .extend({
      top: padding,
      bottom: padding,
      left: padding,
      right: padding,
      background: "#ffffff",
    })
    .resize(size, size, { fit: "contain", background: "#ffffff" })
    .png()
    .toFile(path.join(outputDir, fileName));
}

await sharp(input).png().toFile(path.join(outputDir, "crowscap-logo-source.png"));
await saveIcon(192, "crowscap-icon-192.png", 18);
await saveIcon(512, "crowscap-icon-512.png", 44);
await saveIcon(512, "crowscap-maskable-512.png", 72);
await saveIcon(180, "apple-touch-icon.png", 16);
