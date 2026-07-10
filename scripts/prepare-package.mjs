// จัดไฟล์ก่อน electron-builder: renderer dist + engine exe เข้าที่ที่ config ชี้
import { cpSync, existsSync, rmSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const desktop = join(root, "apps", "desktop");

const jobs = [
  {
    from: join(root, "apps", "renderer", "dist"),
    to: join(desktop, "renderer-dist"),
    name: "renderer",
  },
  {
    from: join(desktop, "engine-dist-build", "aiview-engine"),
    to: join(desktop, "engine-dist"),
    name: "engine",
  },
];

for (const { from, to, name } of jobs) {
  if (!existsSync(from)) {
    console.error(`[prepare-package] missing ${name} build at ${from}`);
    process.exit(1);
  }
  rmSync(to, { recursive: true, force: true });
  cpSync(from, to, { recursive: true });
  console.log(`[prepare-package] ${name}: ${from} -> ${to}`);
}
