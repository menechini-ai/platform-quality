import { clsx } from "clsx";
import { Bot } from "lucide-react";

interface PillProps {
  children: React.ReactNode;
  tone?: "default" | "good" | "warn" | "bad" | "accent";
  className?: string;
  title?: string;
}

export function Pill({ children, tone = "default", className, title }: PillProps) {
  return (
    <span
      title={title}
      className={clsx(
        "pill inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-mono font-medium rounded",
        tone === "good" && "pill-good bg-[rgb(var(--sev-ok)/0.15)] text-[rgb(var(--sev-ok))] border border-[rgb(var(--sev-ok)/0.3)]",
        tone === "warn" && "pill-warn bg-[rgb(var(--sev-warn)/0.15)] text-[rgb(var(--sev-warn))] border border-[rgb(var(--sev-warn)/0.3)]",
        tone === "bad" && "pill-bad bg-[rgb(var(--sev-critical)/0.15)] text-[rgb(var(--sev-critical))] border border-[rgb(var(--sev-critical)/0.3)]",
        tone === "accent" && "pill-accent bg-[rgb(var(--brand)/0.15)] text-[rgb(var(--brand))] border border-[rgb(var(--brand)/0.3)]",
        tone === "default" && "bg-[rgb(var(--ink-700)/0.5)] text-[rgb(var(--ink-300))] border border-[rgb(var(--ink-600)/0.5)]",
        className,
      )}
    >
      {children}
    </span>
  );
}

export function VerdictPill({ verdict }: { verdict: string }) {
  const v = (verdict || "").toLowerCase();
  if (v === "spike") return <Pill tone="bad">spike</Pill>;
  if (v === "known") return <Pill tone="good">known</Pill>;
  if (v === "unknown") return <Pill tone="warn">unknown</Pill>;
  if (v === "") return <Pill>learning</Pill>;
  return <Pill tone="accent">{verdict}</Pill>;
}

export function SourceBadge({ source }: { source?: string }) {
  const s = (source || "").trim();
  if (!s) return null;
  if (s === "agent" || s.startsWith("agent:")) {
    return (
      <Pill tone="accent" className="inline-flex items-center gap-1" title={s}>
        <Bot size={11} />
        <span>AI</span>
      </Pill>
    );
  }
  return <Pill title={s}>{s}</Pill>;
}

export function SeverityBadge({ severity, className }: { severity: string; className?: string }) {
  const sev = severity.toUpperCase();
  if (sev.startsWith("SEV-1") || sev === "CRITICAL") return <Pill tone="bad" className={className}>SEV-1</Pill>;
  if (sev.startsWith("SEV-2") || sev === "HIGH") return <Pill tone="warn" className={className}>SEV-2</Pill>;
  if (sev.startsWith("SEV-3") || sev === "MEDIUM") return <Pill tone="accent" className={className}>SEV-3</Pill>;
  if (sev.startsWith("SEV-4") || sev === "LOW") return <Pill tone="default" className={className}>SEV-4</Pill>;
  return <Pill tone="default" className={className}>{sev}</Pill>;
}

export function StatusBadge({ status, className }: { status: string; className?: string }) {
  const s = (status || "").toLowerCase();
  if (s === "active" || s === "firing") return <Pill tone="bad" className={clsx("capitalize", className)}>{s}</Pill>;
  if (s === "stable" || s === "pending") return <Pill tone="warn" className={clsx("capitalize", className)}>{s}</Pill>;
  if (s === "resolved" || s === "ok") return <Pill tone="good" className={clsx("capitalize", className)}>{s}</Pill>;
  if (s === "acknowledged") return <Pill tone="accent" className={clsx("capitalize", className)}>{s}</Pill>;
  return <Pill tone="default" className={clsx("capitalize", className)}>{s}</Pill>;
}