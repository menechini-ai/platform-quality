import { clsx } from "clsx";
import { X } from "lucide-react";

interface BulkActionBarProps {
  selectedIds: string[];
  onClear: () => void;
  onAction: (action: string) => void;
  actions: { id: string; label: string; disabled?: boolean }[];
  className?: string;
}

export function BulkActionBar({
  selectedIds,
  onClear,
  onAction,
  actions,
  className,
}: BulkActionBarProps) {
  if (selectedIds.length === 0) return null;

  return (
    <div
      className={clsx(
        "bulk-bar fixed bottom-0 left-0 right-0 z-[var(--z-overlay)]",
        "bg-[rgb(var(--surface-raised))] border-t border-[rgb(var(--ink-700)/0.5)] px-4 py-3 animate-[slide-up_200ms_ease-out]",
        className,
      )}
      role="status"
      aria-live="polite"
    >
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <span className="text-sm font-mono text-slate-400">
            {selectedIds.length} selected
          </span>
          <span className="w-px h-6 bg-[rgb(var(--ink-600)/0.5)]" />
          <button
            onClick={onClear}
            className="text-xs text-slate-500 hover:text-slate-300 font-mono flex items-center gap-1"
            aria-label="Clear selection"
          >
            <X size={12} /> Clear
          </button>
        </div>
        <div className="flex items-center gap-2">
          {actions.map((action) => (
            <button
              key={action.id}
              onClick={() => onAction(action.id)}
              disabled={action.disabled}
              className={clsx(
                "px-3 py-1.5 text-sm font-medium rounded-lg transition-colors",
                "bg-[rgb(var(--brand))] hover:bg-[rgb(var(--brand-hover))] text-white",
                action.disabled && "opacity-50 cursor-not-allowed",
              )}
            >
              {action.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

interface RowSelectCheckboxProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  "aria-label"?: string;
}

export function RowSelectCheckbox({ checked, onChange, disabled, "aria-label": ariaLabel }: RowSelectCheckboxProps) {
  return (
    <label className="flex items-center justify-center">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        disabled={disabled}
        aria-label={ariaLabel}
        className={clsx(
          "checkbox w-4 h-4 rounded border-[rgb(var(--ink-600))]",
          "text-[rgb(var(--brand))] focus:ring-[rgb(var(--brand))] focus:ring-2",
          "disabled:opacity-50 disabled:cursor-not-allowed",
        )}
      />
    </label>
  );
}

interface SelectAllCheckboxProps {
  checked: boolean;
  indeterminate: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
}

export function SelectAllCheckbox({ checked, indeterminate, onChange, disabled }: SelectAllCheckboxProps) {
  return (
    <label className="flex items-center justify-center">
      <input
        type="checkbox"
        checked={checked}
        ref={(el) => {
          if (el) el.indeterminate = indeterminate;
        }}
        onChange={(e) => onChange(e.target.checked)}
        disabled={disabled}
        className={clsx(
          "checkbox w-4 h-4 rounded border-[rgb(var(--ink-600))]",
          "text-[rgb(var(--brand))] focus:ring-[rgb(var(--brand))] focus:ring-2",
          "disabled:opacity-50 disabled:cursor-not-allowed",
        )}
      />
    </label>
  );
}