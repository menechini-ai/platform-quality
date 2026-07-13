import { clsx } from "clsx";
import { X } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

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
          "checkbox w-4 h-4 rounded border-slate-600",
          "text-brand-500 focus:ring-brand-500 focus:ring-2",
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
          "checkbox w-4 h-4 rounded border-slate-600",
          "text-brand-500 focus:ring-brand-500 focus:ring-2",
          "disabled:opacity-50 disabled:cursor-not-allowed",
        )}
      />
    </label>
  );
}

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
        "bulk-bar fixed bottom-0 left-0 right-0 z-40 bg-surface-800 border-t border-slate-700/50 px-4 py-3 animate-slide-up",
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
          <span className="w-px h-6 bg-slate-600/50" />
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
                "bg-brand-600 hover:bg-brand-500 text-white",
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

interface UseBulkSelectionOptions<T extends { id: string }> {
  items: T[];
  storageKey: string;
  onSelectionChange?: (ids: string[]) => void;
}

export function useBulkSelection<T extends { id: string }>({
  items,
  storageKey,
  onSelectionChange,
}: UseBulkSelectionOptions<T>) {
  const [selectedIds, setSelectedIds] = useState<string[]>(() => {
    try {
      const saved = localStorage.getItem(storageKey);
      if (saved) return JSON.parse(saved);
    } catch {
      // ignore parse errors
    }
    return [];
  });

  useEffect(() => {
    localStorage.setItem(storageKey, JSON.stringify(selectedIds));
    onSelectionChange?.(selectedIds);
  }, [selectedIds, storageKey, onSelectionChange]);

  const isSelected = useCallback((id: string) => selectedIds.includes(id), [selectedIds]);

  const allSelected = useMemo(
    () => items.length > 0 && items.every((i) => isSelected(i.id)),
    [items, isSelected],
  );
  const someSelected = useMemo(
    () => items.length > 0 && items.some((i) => isSelected(i.id)),
    [items, isSelected],
  );

  const toggleAll = useCallback(() => {
    if (allSelected) {
      setSelectedIds([]);
    } else {
      setSelectedIds(items.map((i) => i.id));
    }
  }, [items, allSelected]);

  const toggleOne = useCallback((id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  }, []);

  const clear = useCallback(() => setSelectedIds([]), []);

  return {
    selectedIds,
    isSelected,
    allSelected,
    someSelected,
    noneSelected: items.length > 0 && !someSelected,
    toggleAll,
    toggleOne,
    clear,
    setSelectedIds,
  };
}