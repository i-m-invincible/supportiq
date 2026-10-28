import { categoryLabel, palette, type Analytics } from '../lib/types';

export function TrendChart({ data }: { data: Analytics['trend'] }) {
  const max = Math.max(4, ...data.map(d => d.total));
  const x = (i: number) => 40 + i * (580 / Math.max(1, data.length - 1));
  const y = (n: number) => 165 - (n / max) * 135;
  const line = data.map((d, i) => `${x(i)},${y(d.total)}`).join(' ');
  const negative = data.map((d, i) => `${x(i)},${y(d.negative)}`).join(' ');
  return <div className="trend-chart"><svg viewBox="0 0 660 205" role="img" aria-label="Daily ticket volume and negative sentiment for the past seven days">
    <defs><linearGradient id="chart-fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#4c997c" stopOpacity="0.19" /><stop offset="100%" stopColor="#4c997c" stopOpacity="0.01" /></linearGradient></defs>
    {[0, 1, 2, 3].map(tick => { const value = Math.round(max * tick / 3); return <g key={tick}><line x1="38" x2="628" y1={y(value)} y2={y(value)} stroke="#e9eeea" strokeDasharray="4 5" /><text x="20" y={y(value) + 4} textAnchor="end" className="chart-label">{value}</text></g>; })}
    {data.length > 0 && <><polygon points={`40,165 ${line} ${x(data.length - 1)},165`} fill="url(#chart-fill)" /><polyline points={line} fill="none" stroke="#287c65" strokeWidth="3" strokeLinejoin="round" /><polyline points={negative} fill="none" stroke="#c29c6c" strokeWidth="2" strokeDasharray="5 5" strokeLinejoin="round" /></>}
    {data.map((d, i) => <g key={d.date}><circle cx={x(i)} cy={y(d.total)} r="4" fill="#fff" stroke="#287c65" strokeWidth="2"><title>{d.date}: {d.total} tickets, {d.negative} negative</title></circle><text x={x(i)} y="193" textAnchor="middle" className="chart-label">{new Date(d.date + 'T12:00:00').toLocaleDateString(undefined, { weekday: 'short' })}</text></g>)}
  </svg><div className="chart-legend"><span><i className="legend-dot green" />All conversations</span><span><i className="legend-dot sand" />Negative sentiment</span></div></div>;
}

export function CategoryChart({ counts }: { counts: Record<string, number> }) {
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  const total = entries.reduce((sum, [, count]) => sum + count, 0);
  return <div className="category-chart"><div className="stacked-bar" role="img" aria-label={`${total} tickets by category`}>{entries.map(([name, count], i) => <div key={name} style={{ width: `${count / Math.max(1, total) * 100}%`, background: palette[i % palette.length] }} title={`${categoryLabel(name)}: ${count}`} />)}</div>
    <div className="category-list">{entries.map(([name, count], i) => <div key={name}><span><i className="legend-dot" style={{ background: palette[i % palette.length] }} />{categoryLabel(name)}</span><span><b>{count}</b><small>{Math.round(count / Math.max(1, total) * 100)}%</small></span></div>)}</div>
  </div>;
}

export function Distribution({ values, labels = {} }: { values: Record<string, number>; labels?: Record<string, string> }) {
  const max = Math.max(1, ...Object.values(values));
  return <div className="distribution">{Object.entries(values).map(([label, count], i) => <div className="distribution-row" key={label}><span>{labels[label] || label.replace('_', ' ')}</span><div><i style={{ width: `${count / max * 100}%`, background: palette[i % palette.length] }} /></div><b>{count}</b></div>)}</div>;
}
