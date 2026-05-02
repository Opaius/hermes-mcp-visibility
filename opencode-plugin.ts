import type { Plugin } from "@opencode-ai/plugin"
import { createHash } from "node:crypto"
import { existsSync, mkdirSync, readFileSync, writeFileSync, unlinkSync, statSync } from "node:fs"
import { join } from "node:path"

const SECURITY_ENABLED = process.env.MCP_VISIBILITY_SECURITY !== "0"
const TOON_ENABLED = process.env.MCP_VISIBILITY_TOON !== "0"
const CACHE_ENABLED = process.env.MCP_VISIBILITY_CACHE !== "0"
const CACHE_DIR = join(process.env.TMPDIR || "/tmp", "opencode-mcp-vis-cache")

const DANGEROUS_PATTERNS = [
  /\brm\s+-rf\s+\/\b/, /\bmkfs\b/, /\bdd\s+if=/, />\s*\/dev\/sd/,
  /\bchmod\s+777\b/, /\bshutdown\b/, /\breboot\b/,
  /\bkill\s+-9\s+1\b/, /\b:(){ :\|:& };:/,
  /\bwget\s.*\|\s*sh/, /\bcurl\s.*\|\s*sh/, /\bcurl\s.*\|\s*bash/,
]

function checkSecurity(code: string): string | null {
  if (!SECURITY_ENABLED) return null
  for (const p of DANGEROUS_PATTERNS) {
    if (p.test(code)) return JSON.stringify({ output: "", exit_code: -1, error: `⛔ BLOCKED: ${p.source}`, status: "blocked" })
  }
  return null
}

function jsonToToon(data: unknown): string {
  if (Array.isArray(data)) {
    if (data.length === 0) return "[]"
    if (data.every(x => typeof x === "object" && x !== null)) {
      const keys = Object.keys(data[0])
      return `items[${data.length}]{${keys.join(",")}}\n` + data.map(item => `  ${keys.map(k => String((item as any)[k] ?? "")).join(",")}`).join("\n")
    }
    return JSON.stringify(data)
  }
  if (typeof data === "object" && data !== null) {
    const parts: string[] = []
    for (const [k, v] of Object.entries(data as Record<string, unknown>)) {
      if (Array.isArray(v) && v.length > 0 && v.every(x => typeof x === "object")) {
        const keys = Object.keys(v[0])
        parts.push(`${k}[${v.length}]{${keys.join(",")}}`)
        for (const item of v) parts.push(`  ${keys.map(kk => String((item as any)[kk] ?? "")).join(",")}`)
      } else if (typeof v === "number" || typeof v === "boolean" || v === null) {
        parts.push(`${k}=${v}`)
      } else if (typeof v === "string") {
        parts.push(/[,=\n ]/.test(v) ? `${k}=${JSON.stringify(v)}` : `${k}=${v}`)
      } else {
        parts.push(`${k}=${JSON.stringify(v)}`)
      }
    }
    return parts.join("\n")
  }
  return JSON.stringify(data)
}

function toonConvert(dataStr: string): string {
  if (!TOON_ENABLED) return dataStr
  const stripped = dataStr.trim()
  if (!(stripped.startsWith("{") || stripped.startsWith("["))) return dataStr
  try {
    const toon = jsonToToon(JSON.parse(stripped))
    return toon.length < dataStr.length ? toon : dataStr
  } catch { return dataStr }
}

function cacheKey(tool: string, args: Record<string, unknown>): string {
  return createHash("sha256").update(`${tool}:${JSON.stringify(args, Object.keys(args).sort())}`).digest("hex").slice(0, 16)
}

function cacheGet(tool: string, args: Record<string, unknown>): string | null {
  if (!CACHE_ENABLED) return null
  try {
    const p = join(CACHE_DIR, `${cacheKey(tool, args)}.result`)
    if (!existsSync(p)) return null
    if ((Date.now() - statSync(p).mtimeMs) / 1000 > 60) { unlinkSync(p); return null }
    return readFileSync(p, "utf-8")
  } catch { return null }
}

function cacheSet(tool: string, args: Record<string, unknown>, result: string): void {
  if (!CACHE_ENABLED) return
  try {
    if (!existsSync(CACHE_DIR)) mkdirSync(CACHE_DIR, { recursive: true })
    writeFileSync(join(CACHE_DIR, `${cacheKey(tool, args)}.result`), result)
  } catch {}
}

export const McpVisibilityPlugin: Plugin = async ({}) => {
  return {
    "tool.execute.before": async (input, output) => {
      const tool = String(input?.tool ?? "")
      if (tool.includes("ctx_execute") || tool.includes("ctx_batch")) {
        const args = output?.args as Record<string, unknown> | undefined
        if (!args) return
        const inner = (args.arguments ?? args) as Record<string, unknown>
        const code = String(inner.code ?? "")
        const lang = String(inner.language ?? "")
        if (lang === "shell" && code) {
          const blocked = checkSecurity(code)
          if (blocked) {
            args.code = `echo '${blocked.replace(/'/g, "'\\''")}'`
            args.language = "shell"
          }
        }
      }
    },

    "tool.execute.after": async (input, output: any) => {
      const tool = String(input?.tool ?? "")
      if (!tool.includes("ctx_") && !tool.includes("searxng")) return

      // content is array of content blocks (Anthropic/OpenCode format)
      let result = ""
      const content = output?.content
      if (Array.isArray(content)) {
        for (const block of content) {
          if (block.type === "text" && typeof block.text === "string") result += block.text
        }
      } else if (typeof content === "string") {
        result = content
      }
      if (!result) return

      const args = (input?.args ?? {}) as Record<string, unknown>

      // Cache check
      const cached = cacheGet(tool, args)
      if (cached) {
        if (Array.isArray(content)) {
          for (const block of content) {
            if (block.type === "text") { block.text = cached; break }
          }
        }
        return
      }

      // TOON conversion
      const converted = toonConvert(result)
      if (converted !== result) {
        if (Array.isArray(content)) {
          for (const block of content) {
            if (block.type === "text" && block.text === result) { block.text = converted; break }
          }
        }
      }

      cacheSet(tool, args, converted)
    },
  }
}
