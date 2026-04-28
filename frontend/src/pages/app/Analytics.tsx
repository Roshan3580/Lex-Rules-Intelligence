import { Area, AreaChart, Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const extractionData = [
  { day: "Mon", rules: 142, prev: 98 },
  { day: "Tue", rules: 168, prev: 110 },
  { day: "Wed", rules: 219, prev: 134 },
  { day: "Thu", rules: 187, prev: 156 },
  { day: "Fri", rules: 245, prev: 142 },
  { day: "Sat", rules: 98, prev: 67 },
  { day: "Sun", rules: 76, prev: 54 },
];

const rejectionData = [
  { week: "W1", prevented: 12, slipped: 2 },
  { week: "W2", prevented: 18, slipped: 1 },
  { week: "W3", prevented: 24, slipped: 3 },
  { week: "W4", prevented: 31, slipped: 1 },
  { week: "W5", prevented: 28, slipped: 0 },
  { week: "W6", prevented: 42, slipped: 2 },
];

const sourceChanges = [
  { month: "Jan", changes: 23 },
  { month: "Feb", changes: 31 },
  { month: "Mar", changes: 28 },
  { month: "Apr", changes: 47 },
  { month: "May", changes: 39 },
  { month: "Jun", changes: 56 },
];

const tooltipStyle = {
  backgroundColor: "hsl(var(--popover))",
  border: "1px solid hsl(var(--border))",
  borderRadius: "0.75rem",
  fontSize: "12px",
  padding: "8px 12px",
};

const Analytics = () => {
  return (
    <div className="p-6 lg:p-8 space-y-6 max-w-[1600px]">
      <div>
        <p className="text-xs uppercase tracking-widest text-muted-foreground">Insights</p>
        <h1 className="text-3xl font-bold tracking-tight mt-1">Analytics</h1>
        <p className="text-sm text-muted-foreground mt-1">Operational metrics across your rule estate.</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: "Rules extracted (30d)", value: "1,847", delta: "+24%" },
          { label: "Rejections prevented", value: "127", delta: "+38%" },
          { label: "Source changes detected", value: "56", delta: "+18%" },
          { label: "Avg review time", value: "4m 12s", delta: "-22%" },
        ].map((k) => (
          <div key={k.label} className="rounded-2xl glass p-5">
            <p className="text-xs text-muted-foreground">{k.label}</p>
            <p className="text-2xl font-bold mt-2">{k.value}</p>
            <p className={`text-[11px] mt-1 ${k.delta.startsWith("-") ? "text-destructive" : "text-success"}`}>{k.delta} vs last period</p>
          </div>
        ))}
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <div className="rounded-2xl glass p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-base font-semibold">Rule extraction volume</h3>
              <p className="text-xs text-muted-foreground">This week vs last week</p>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={extractionData}>
              <defs>
                <linearGradient id="ruleGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity={0.5} />
                  <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
              <XAxis dataKey="day" stroke="hsl(var(--muted-foreground))" fontSize={11} tickLine={false} axisLine={false} />
              <YAxis stroke="hsl(var(--muted-foreground))" fontSize={11} tickLine={false} axisLine={false} />
              <Tooltip contentStyle={tooltipStyle} />
              <Area type="monotone" dataKey="prev" stroke="hsl(var(--muted-foreground))" strokeOpacity={0.5} strokeDasharray="4 4" fill="transparent" strokeWidth={1.5} />
              <Area type="monotone" dataKey="rules" stroke="hsl(var(--primary))" fill="url(#ruleGrad)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="rounded-2xl glass p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-base font-semibold">Rejection prevention</h3>
              <p className="text-xs text-muted-foreground">Issues caught before submission</p>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={rejectionData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
              <XAxis dataKey="week" stroke="hsl(var(--muted-foreground))" fontSize={11} tickLine={false} axisLine={false} />
              <YAxis stroke="hsl(var(--muted-foreground))" fontSize={11} tickLine={false} axisLine={false} />
              <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "hsl(var(--secondary) / 0.5)" }} />
              <Bar dataKey="prevented" fill="hsl(var(--success))" radius={[4, 4, 0, 0]} />
              <Bar dataKey="slipped" fill="hsl(var(--destructive))" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="rounded-2xl glass p-6 lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-base font-semibold">Source change frequency</h3>
              <p className="text-xs text-muted-foreground">Tracked regulatory updates over time</p>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={sourceChanges}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
              <XAxis dataKey="month" stroke="hsl(var(--muted-foreground))" fontSize={11} tickLine={false} axisLine={false} />
              <YAxis stroke="hsl(var(--muted-foreground))" fontSize={11} tickLine={false} axisLine={false} />
              <Tooltip contentStyle={tooltipStyle} />
              <Line type="monotone" dataKey="changes" stroke="hsl(var(--teal))" strokeWidth={2.5} dot={{ fill: "hsl(var(--teal))", r: 4 }} activeDot={{ r: 6 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

export default Analytics;
