/** System specs สำหรับ VRAM-gated install (F7 / AI_MODELS.md) */
import { execFile } from "child_process";
import * as os from "os";

export interface SystemSpecs {
  ram_mb: number;
  vram_mb: number | null; // null = ไม่พบ NVIDIA GPU / อ่านไม่ได้
  gpu_name: string | null;
}

function nvidiaSmi(): Promise<{ vram_mb: number; gpu_name: string } | null> {
  return new Promise((resolve) => {
    execFile(
      "nvidia-smi",
      ["--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
      { timeout: 5000 },
      (err, stdout) => {
        if (err || !stdout.trim()) return resolve(null);
        const [name, mem] = stdout.trim().split("\n")[0].split(",");
        const vram = Number(mem?.trim());
        resolve(Number.isFinite(vram) ? { vram_mb: vram, gpu_name: name.trim() } : null);
      },
    );
  });
}

export async function getSystemSpecs(): Promise<SystemSpecs> {
  const gpu = await nvidiaSmi();
  return {
    ram_mb: Math.round(os.totalmem() / 1024 / 1024),
    vram_mb: gpu?.vram_mb ?? null,
    gpu_name: gpu?.gpu_name ?? null,
  };
}
