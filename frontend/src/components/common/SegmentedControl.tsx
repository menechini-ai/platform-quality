import { clsx } from "clsx";
import { useSearchParams } from "react-router-dom";

interface SegmentedControlProps {
  param: string;
  defaultValue: string;
  options: { value: string; label: string; badge?: number }[];
  ariaLabel?: string;
  className?: string;
}

export function SegmentedControl({
  param,
  defaultValue,
  options,
  ariaLabel,
  className,
}: SegmentedControlProps) {
  const [searchParams, setSearchParams] = useSearchParams();

  const current = searchParams.get(param) ?? defaultValue;

  const handleChange = (value: string) => {
    const next = new URLSearchParams(searchParams);
    if (value === defaultValue) {
      next.delete(param);
    } else {
      next.set(param, value);
    }
    next.delete("page");
    setSearchParams(next, { replace: true });
  };

  return (
    <div
      role="group"
      aria-label={ariaLabel}
      className={clsx("seg-ctrl flex items-center gap-1 bg-[rgb(var(--surface-raised)/0.5)] p-0.5 rounded-lg", className)}
    >
      {options.map((opt) => {
        const active = current === opt.value;
        return (
          <button
            key={opt.value}
            type="button"
            onClick={() => handleChange(opt.value)}
            className={clsx(
              "seg-btn relative px-3 py-1.5 text-sm font-medium rounded-md transition-colors",
              active
                ? "bg-[rgb(var(--brand)/0.2)] text-[rgb(var(--brand))] shadow-[inset_0_-2px_0_rgb(var(--brand))]"
                : "text-[rgb(var(--ink-400))] hover:text-[rgb(var(--ink-200))] hover:bg-[rgb(var(--ink-700)/0.5)]",
            )}
            aria-pressed={active}
            aria-label={opt.label}
          >
            {opt.label}
            {opt.badge !== undefined && opt.badge > 0 && (
              <span
                className={clsx(
                  "seg-badge absolute -top-1 -right-1 w-4 h-4 text-[9px] font-mono rounded-full flex items-center justify-center",
                  active
                    ? "bg-[rgb(var(--brand))] text-white"
                    : "bg-[rgb(var(--ink-700))] text-[rgb(var(--ink-300))]",
                )}
              >
                {opt.badge > 99 ? "99+" : opt.badge}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}