// @vitest-environment node
// Enforces the portal structure (see .docs/development/portal-architecture.md). A broken rule
// fails the test, so the layering cannot drift silently as screens are added.
import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join, normalize, relative, sep } from "node:path";
import { describe, expect, it } from "vitest";

const SRC = join(import.meta.dirname, "..", "src");

type Layer = "model" | "api" | "services" | "store" | "hooks" | "ui" | "routes" | "index";

// Inside one feature: which layers each layer may import.
const ALLOWED: Record<Layer, Layer[]> = {
  model: ["model"],
  api: ["api", "model"],
  services: ["services", "model"],
  store: ["store", "model"],
  hooks: ["hooks", "api", "services", "store", "model"],
  ui: ["ui", "hooks", "services", "model"],
  routes: ["ui"],
  index: ["model", "api", "services", "store", "hooks", "ui", "routes"],
};
// Packages that pure layers must not use (they would bring state, rendering or HTTP in).
const FRAMEWORKS = ["react", "react-dom", "react-router", "@tanstack/react-query", "zustand"];
const PURE: Layer[] = ["model", "services", "api"];

function files(directory: string): string[] {
  return readdirSync(directory).flatMap((name: string) => {
    const path = join(directory, name);
    return statSync(path).isDirectory() ? files(path) : /\.tsx?$/.test(name) ? [path] : [];
  });
}

function imports(source: string): string[] {
  const pattern = /(?:import|export)\s[^;]*?from\s+["']([^"']+)["']|import\s+["']([^"']+)["']/g;
  const found = source.matchAll(pattern);
  return [...found].map((match) => match[1] ?? match[2] ?? "");
}

/** "src/features/quotations/hooks/x.ts" -> ["features", "quotations", "hooks", ...]. */
function parts(file: string): string[] {
  return relative(SRC, file).split(sep);
}

function target(file: string, specifier: string): string[] | null {
  if (specifier.startsWith("@/")) return specifier.slice(2).split("/");
  if (specifier.startsWith(".")) return relative(SRC, normalize(join(dirname(file), specifier))).split(sep);
  return null; // a package
}

function featureLayer(path: string[]): Layer {
  const name = path[2] ?? "";
  if (name.startsWith("index")) return "index";
  if (name.startsWith("routes")) return "routes";
  return name as Layer;
}

function violations(): string[] {
  const problems: string[] = [];
  for (const file of files(SRC)) {
    const from = parts(file);
    const source = readFileSync(file, "utf8");
    const label = from.join("/");
    if (/\bfetch\(/.test(source) && label !== "shared/api/httpClient.ts") {
      problems.push(`${label} calls fetch directly; use a repository and shared/api/httpClient`);
    }
    // Phase 2: tokens (API keys, email links) must never end up in browser storage. Only the
    // selected business is remembered, in the tenant store.
    if (/\b(localStorage|sessionStorage|indexedDB)\b/.test(source) && !label.startsWith("features/tenant/store/")) {
      problems.push(`${label} uses browser storage; only features/tenant/store may`);
    }
    for (const specifier of imports(source)) {
      const to = target(file, specifier);
      if (to === null) {
        if (from[0] === "features" && PURE.includes(featureLayer(from)) && FRAMEWORKS.includes(specifier)) {
          problems.push(`${label} (${featureLayer(from)}) must not import ${specifier}`);
        }
        continue;
      }
      if (from[0] === "shared" && to[0] !== "shared") {
        problems.push(`${label}: shared code must not import ${specifier}`);
      }
      if (to[0] === "features" && from[1] !== to[1] && to.length > 2 && !to[2]?.startsWith("index")) {
        problems.push(`${label} reaches into ${specifier}; import the feature's index instead`);
      }
      if (from[0] === "features" && to[0] === "features" && from[1] === to[1]) {
        const layer = featureLayer(from);
        const wanted = featureLayer(to);
        if (!ALLOWED[layer].includes(wanted)) {
          problems.push(`${label} (${layer}) must not import ${wanted}: ${specifier}`);
        }
      }
      if (from[0] === "features" && to[0] === "app") {
        problems.push(`${label}: features must not import the app shell`);
      }
    }
  }
  return problems;
}

describe("portal architecture", () => {
  it("keeps layers and feature boundaries", () => {
    expect(violations()).toEqual([]);
  });

  it("keeps test files out of src", () => {
    expect(files(SRC).filter((file) => /\.test\.tsx?$/.test(file))).toEqual([]);
  });

  it("gives every feature a public index", () => {
    const features = readdirSync(join(SRC, "features"));
    for (const feature of features) {
      expect(readdirSync(join(SRC, "features", feature)), feature).toContain("index.ts");
    }
  });
});
