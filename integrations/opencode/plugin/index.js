// warrant for OpenCode. One file, both plugin APIs: V1 calls server() (OpenCode 1.18.29+),
// V2 calls setup() (OpenCode 2). Install as a single file in plugin/ so both versions load it.
// Bridges OpenCode events to the same hook handlers Claude Code and Codex use:
//   tool.execute.after      -> capture tool output as evidence      (warrant hook post)
//   session prompt          -> record the prompt, anchor the question (warrant hook prompt)
//   session experimental.idle -> check the finished reply; if a number, citation or
//                                statistic fails, send one follow-up prompt with the reason
// Quiet by default: the Python side does nothing in projects without `warrant init`.
import { spawn } from "node:child_process"
import { join } from "node:path"

const ROOT = process.env.WARRANT_ROOT || "__WARRANT_ROOT__" // set by scripts/install.sh
const SCRIPT = join(ROOT, "bin", "warrant.py")
const PYTHONS = process.platform === "win32" ? ["python", "py", "python3"] : ["python3", "python"]
const PREFIX = "[warrant]"
// WARRANT_DEBUG=1 appends plugin events to ~/.warrant-opencode.log (for diagnosing hosts)
import { appendFileSync } from "node:fs"
import { homedir } from "node:os"
function debug(...a) {
  if (!process.env.WARRANT_DEBUG) return
  try { appendFileSync(join(homedir(), ".warrant-opencode.log"), new Date().toISOString() + " " + a.map((x) => typeof x === "string" ? x : JSON.stringify(x)).join(" ") + "\n") } catch {}
}

function runOnce(py, name, payload) {
  return new Promise((resolve) => {
    let out = ""
    let child
    try {
      child = spawn(py, [SCRIPT, "hook", name], { stdio: ["pipe", "pipe", "ignore"] })
    } catch {
      return resolve(undefined)
    }
    child.on("error", () => resolve(undefined)) // interpreter not found: try the next one
    child.stdout.on("data", (d) => (out += d))
    child.on("close", () => {
      try {
        resolve(out.trim() ? JSON.parse(out) : null)
      } catch {
        resolve(null)
      }
    })
    child.stdin.end(JSON.stringify(payload))
  })
}

let python
async function run(name, payload) {
  for (const py of python ? [python] : PYTHONS) {
    const res = await runOnce(py, name, payload)
    if (res !== undefined) {
      python = py
      return res && Object.keys(res).length ? res : null
    }
  }
  return null // no Python: a supervisor must never break the session
}

// pull the text of the latest assistant message out of whatever shape the server returns
function lastAssistantText(messages) {
  const list = Array.isArray(messages) ? messages : messages?.items || messages?.data || []
  for (let i = list.length - 1; i >= 0; i--) {
    const m = list[i]
    const role = m?.role || m?.info?.role || m?.type
    if (role !== "assistant") continue
    const texts = []
    const walk = (v) => {
      if (!v || typeof v !== "object") return
      if (Array.isArray(v)) return v.forEach(walk)
      if (v.type === "text" && typeof v.text === "string") texts.push(v.text)
      for (const k of ["parts", "content", "items"]) if (v[k]) walk(v[k])
    }
    walk(m)
    if (texts.length) return texts.join("\n")
  }
  return ""
}

// --- V1 (OpenCode 1.x): one object of hooks ------------------------------------------
async function server({ client, directory }) {
  const cwd = directory || process.cwd()
  const args = new Map() // callID -> tool args (V1 passes them to "before" only)
  const nudged = new Set()
  let anchor = ""
  let started = false
  const roles = new Map() // messageID -> role
  const texts = new Map() // messageID -> Map(partID -> text)
  const lastAssistant = new Map() // sessionID -> latest assistant messageID
  return {
    "tool.execute.before": async (input, output) => {
      args.set(input.callID, output?.args)
    },
    "tool.execute.after": async (input, output) => {
      const toolInput = args.get(input.callID) || {}
      args.delete(input.callID)
      await run("post", { tool_name: input.tool, tool_input: toolInput, tool_response: output?.output, cwd })
    },
    "chat.message": async (_input, output) => {
      const text = (output?.parts || []).filter((p) => p.type === "text").map((p) => p.text).join("\n")
      if (!text || text.startsWith(PREFIX)) return
      const res = await run("prompt", { prompt: text, cwd })
      anchor = res?.hookSpecificOutput?.additionalContext || anchor
    },
    "experimental.chat.system.transform": async (_input, output) => {
      if (!started) {
        started = true // session-start context once: question, claim tally, graveyard
        const res = await run("session", { cwd })
        anchor = res?.hookSpecificOutput?.additionalContext || anchor
      }
      if (anchor && Array.isArray(output?.system)) output.system.push(anchor)
    },
    event: async ({ event }) => {
      const props = event?.properties || {}
      // collect the assistant's text from the stream: no API call needed at idle
      if (event?.type === "message.updated" && props.info?.id) {
        roles.set(props.info.id, props.info.role)
        if (props.info.role === "assistant") lastAssistant.set(props.sessionID || props.info.sessionID, props.info.id)
        return
      }
      if (event?.type === "message.part.updated" && props.part?.type === "text") {
        const m = props.part.messageID
        const parts = texts.get(m) || new Map()
        parts.set(props.part.id, props.part.text || "")
        texts.set(m, parts)
        return
      }
      if (event?.type !== "session.idle") return
      const sessionID = props.sessionID
      if (!sessionID) return
      if (nudged.has(sessionID)) return void nudged.delete(sessionID)
      const mid = lastAssistant.get(sessionID)
      let text = mid && texts.has(mid) ? [...texts.get(mid).values()].join("\n") : ""
      if (!text) {
        try {
          const res0 = await client.session.messages({ path: { id: sessionID } })
          text = lastAssistantText(res0?.data ?? res0)
        } catch (e) {
          debug("messages failed", String(e))
        }
      }
      debug("idle check", sessionID, text.slice(0, 80))
      if (!text) return
      const res = await run("stop", { last_assistant_message: text, cwd })
      debug("stop result", res)
      if (res?.decision === "block" && res.reason) {
        nudged.add(sessionID)
        await client.session.prompt({ path: { id: sessionID }, body: { parts: [{ type: "text", text: res.reason }] } })
      }
    },
  }
}

// --- V2 (OpenCode 2.x): register hooks on the context -----------------------------------
export default {
  id: "warrant",
  server,
  async setup(ctx) {
    const cwd = ctx.location?.directory || process.cwd()
    const nudged = new Set()

    await ctx.tool.hook("execute.after", async (event) => {
      if (event.status !== "completed") return
      await run("post", { tool_name: event.tool, tool_input: event.input, tool_response: event.result, cwd })
    })

    await ctx.session.hook("prompt", async (event) => {
      const text = event.prompt?.text || ""
      if (text.startsWith(PREFIX)) return // our own follow-up: not user evidence
      const res = await run("prompt", { prompt: text, cwd })
      const ctxText = res?.hookSpecificOutput?.additionalContext
      if (ctxText && event.sessionID && ctx.session.instructions?.entry?.put) {
        await ctx.session.instructions.entry.put({ sessionID: event.sessionID, key: "warrant", value: ctxText })
      }
    })

    await ctx.session.hook("experimental.idle", async (event) => {
      const sessionID = event.sessionID
      if (nudged.has(sessionID)) return void nudged.delete(sessionID) // block at most once per turn
      const messages = await ctx.session.context({ sessionID })
      const text = lastAssistantText(messages)
      if (!text) return
      const res = await run("stop", { last_assistant_message: text, cwd })
      if (res?.decision === "block" && res.reason) {
        nudged.add(sessionID)
        await ctx.session.prompt({ sessionID, text: res.reason })
      }
    })
  },
}
