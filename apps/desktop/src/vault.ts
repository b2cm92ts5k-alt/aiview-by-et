/**
 * Encrypted API-key vault (TDD.md §9):
 * values encrypted with Electron safeStorage (OS keychain: DPAPI/Keychain/libsecret),
 * stored as base64 blobs in userData/vault.json.
 * No getKey IPC — keys never leave main in plaintext.
 */
import { app, safeStorage } from "electron";
import { promises as fs } from "fs";
import * as path from "path";

function vaultPath(): string {
  return path.join(app.getPath("userData"), "vault.json");
}

async function readVault(): Promise<Record<string, string>> {
  try {
    return JSON.parse(await fs.readFile(vaultPath(), "utf-8"));
  } catch {
    return {};
  }
}

export async function setKey(provider: string, key: string): Promise<void> {
  if (!safeStorage.isEncryptionAvailable()) {
    throw new Error("OS encryption unavailable — refusing to store API key");
  }
  const vault = await readVault();
  vault[provider] = safeStorage.encryptString(key).toString("base64");
  await fs.writeFile(vaultPath(), JSON.stringify(vault), "utf-8");
}

export async function hasKey(provider: string): Promise<boolean> {
  const vault = await readVault();
  return Object.prototype.hasOwnProperty.call(vault, provider);
}

/** main-only (never exposed over IPC): decrypt for in-memory handoff to engine */
export async function getKeyForEngine(provider: string): Promise<string | null> {
  const vault = await readVault();
  const blob = vault[provider];
  if (!blob) return null;
  return safeStorage.decryptString(Buffer.from(blob, "base64"));
}

export async function listKeyProviders(): Promise<string[]> {
  return Object.keys(await readVault());
}

export async function deleteKey(provider: string): Promise<void> {
  const vault = await readVault();
  delete vault[provider];
  await fs.writeFile(vaultPath(), JSON.stringify(vault), "utf-8");
}
