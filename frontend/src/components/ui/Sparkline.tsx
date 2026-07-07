/** Mini sparkline SVG — 100% width, 32px height, cyan line on dark bg. */
export function Sparkline({ data, className = "" }: { data: number[]; className?: string }) {
  if (data.length < 2) return null;

  const w = 120;
  const h = 32;
  const pad = 2;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;

  const points = data.map((v, i) => {
    const x = pad + (i / (data.length - 1)) * (w - 2 * pad);
    const y = h - pad - ((v - min) / range) * (h - 2 * pad);
    return `${x},${y}`;
  });

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className={`w-full h-8 ${className}`} preserveAspectRatio="none">
      <polyline
        fill="none"
        stroke="#06b6d4"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        points={points.join(" ")}
      />
    </svg>
  );
}
