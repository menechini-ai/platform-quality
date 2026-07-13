import { useCallback, useEffect, useMemo, useState } from "react";

interface UseBulkSelectionOptions {
  items: { id: string }[];
  storageKey: string;
  onSelectionChange?: (ids: string[]) => void;
}

interface UseBulkSelectionReturn {
  selectedIds: string[];
  isSelected: (id: string) => boolean;
  allSelected: boolean;
  someSelected: boolean;
  noneSelected: boolean;
  toggleAll: () => void;
  toggleOne: (id: string) => void;
  clear: () => void;
  setSelectedIds: React.Dispatch<React.SetStateAction<string[]>>;
}

export function useBulkSelection({
  items,
  storageKey,
  onSelectionChange,
}: UseBulkSelectionOptions): UseBulkSelectionReturn {
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
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
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