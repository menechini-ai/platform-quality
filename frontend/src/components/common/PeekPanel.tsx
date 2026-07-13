import { clsx } from "clsx";
import { X, ChevronRight } from "lucide-react";
import { useEffect, useRef } from "react";
import { createPortal } from "react-dom";

interface PeekPanelProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  className?: string;
}

export function PeekPanel({ isOpen, onClose, title, children, className }: PeekPanelProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const prevFocus = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    prevFocus.current = document.activeElement as HTMLElement;
    document.body.style.overflow = "hidden";
    panelRef.current?.focus();
    return () => {
      document.body.style.overflow = "";
      prevFocus.current?.focus();
    };
  }, [isOpen]);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    if (isOpen) {
      document.addEventListener("keydown", onKeyDown);
      return () => document.removeEventListener("keydown", onKeyDown);
    }
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return createPortal(
    <div className="fixed inset-0 z-[var(--z-modal)] flex items-end md:items-center justify-center">
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm animate-fade-in"
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        ref={panelRef}
        tabIndex={-1}
        className={clsx(
          "peek-panel w-full max-w-2xl md:max-w-3xl md:w-[calc(100%-2rem)] max-h-[90vh] md:max-h-[80vh]",
          "bg-[rgb(var(--surface-raised))] border-l border-[rgb(var(--ink-700)/0.5)]",
          "shadow-[0_0_32px_rgb(0,0,0,0.4)] animate-[peek-in_200ms_ease-out]",
          className,
        )}
        role="dialog"
        aria-modal="true"
        aria-labelledby="peek-title"
      >
        <div className="flex items-center justify-between px-4 py-3 border-b border-[rgb(var(--ink-700)/0.5)] sticky top-0 bg-[rgb(var(--surface-raised))] backdrop-blur z-10 rounded-t-xl md:rounded-tl-xl md:rounded-tr-xl">
          <h2 id="peek-title" className="text-sm font-semibold text-white font-mono">
            {title}
          </h2>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-500 hover:text-white hover:bg-[rgb(var(--ink-700)/0.5)] transition-colors"
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </div>
        <div className="overflow-y-auto p-4 md:p-6">{children}</div>
      </div>
    </div>,
    document.body,
  );
}

interface PeekFieldProps {
  label: string;
  value?: string | number | null;
  empty?: string;
  className?: string;
  children?: React.ReactNode;
  copyable?: boolean;
}

export function PeekField({
  label,
  value,
  empty = "—",
  className,
  children,
  copyable = false,
}: PeekFieldProps) {
  const display = children ?? (value ?? empty);
  const isEmpty = value === null || value === undefined || value === "";

  return (
    <div className={clsx("peek-field flex flex-col gap-1", className)}>
      <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider">
        {label}
      </span>
      <div className={clsx("flex items-center gap-2 font-mono text-sm", isEmpty && "text-slate-500")}>
        <span className="break-all whitespace-pre-wrap">{display}</span>
        {copyable && typeof value === "string" && !isEmpty && (
          <button
            onClick={() => navigator.clipboard.writeText(value)}
            className="p-0.5 rounded text-slate-500 hover:text-white hover:bg-[rgb(var(--ink-700)/0.5)] opacity-0 group-hover:opacity-100 transition-opacity"
            aria-label="Copy"
          >
            <ChevronRight size={12} className="rotate-90" />
          </button>
        )}
      </div>
    </div>
  );
}

export function PeekSection({ title, children, className }: { title: string; children: React.ReactNode; className?: string }) {
  return (
    <section className={clsx("peek-section space-y-4", className)}>
      <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider border-b border-[rgb(var(--ink-700)/0.5)] pb-2">
        {title}
      </h3>
      <div className="space-y-3">{children}</div>
    </section>
  );
}