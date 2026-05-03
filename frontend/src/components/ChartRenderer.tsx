import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from "recharts";

const COLORS = ["#3b82f6","#10b981","#f59e0b","#ef4444","#8b5cf6"];

interface Props { type: "bar"|"line"|"pie"|"table"; data: any[]; xKey?: string; yKey?: string; }

export function ChartRenderer({ type, data, xKey = "name", yKey = "value" }: Props) {
  if (type === "pie") return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart><Pie data={data} dataKey={yKey} nameKey={xKey} cx="50%" cy="50%" outerRadius={100} label>
        {data.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
      </Pie><Tooltip /><Legend /></PieChart>
    </ResponsiveContainer>
  );
  if (type === "line") return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data}><XAxis dataKey={xKey} /><YAxis /><Tooltip />
        <Line type="monotone" dataKey={yKey} stroke="#3b82f6" strokeWidth={2} /></LineChart>
    </ResponsiveContainer>
  );
  if (type === "table") return (
    <table className="w-full text-sm border-collapse">
      <thead><tr>{Object.keys(data[0] || {}).map((k) => <th key={k} className="border px-3 py-1 bg-gray-50 text-left">{k}</th>)}</tr></thead>
      <tbody>{data.map((row, i) => <tr key={i}>{Object.values(row).map((v: any, j) => <td key={j} className="border px-3 py-1">{v}</td>)}</tr>)}</tbody>
    </table>
  );
  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data}><XAxis dataKey={xKey} /><YAxis /><Tooltip />
        <Bar dataKey={yKey} fill="#3b82f6" radius={[4,4,0,0]} /></BarChart>
    </ResponsiveContainer>
  );
}
