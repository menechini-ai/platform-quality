import { useState } from "react";
import { Search } from "lucide-react";

export function TagFilter({
  tags,
  onChange,
  placeholder = "tags...",
}: {
  tags: string[];
  onChange: (tags: string[]) => void;
  placeholder?: string;
}) {
  const [input, setInput] = useState("");

  const add = () => {
    const t = input.trim();
    if (t && !tags.includes(t)) onChange([...tags, t]);
    setInput("");
  };

  const remove = (t: string) => onChange(tags.filter((x) => x !== t));

  return (
    <div className="flex items-center gap-1.5">
      <div className="flex items-center gap-1 bg-surface-700/60 rounded-md px-2 py-1 text-xs">
        <Search className="w-3 h-3 text-slate-500 shrink-0" />
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && add()}
          placeholder={placeholder}
          className="w-20 bg-transparent outline-none text-slate-300 placeholder-slate-600 font-mono text-xs"
        />
      </div>
      {tags.map((t) => (
        <span
          key={t}
          className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono bg-brand-500/20 text-brand-400"
        >
          {t}
          <button onClick={() => remove(t)} className="hover:text-white">
            ×
          </button>
        </span>
      ))}
    </div>
  );
}
