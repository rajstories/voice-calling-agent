import { 
  TrendingUp, 
  PhoneCall, 
  Clock, 
  PiggyBank, 
  BarChart3, 
  CheckCircle2, 
  Voicemail, 
  CalendarClock 
} from "lucide-react";

export default function Dashboard() {
  return (
    <div className="flex flex-col gap-8">
      {/* Greeting Section */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">Good afternoon, Raj</h1>
        <p className="mt-1 text-base text-slate-500">UPM Consultancy Workspace</p>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* Card 1: Total Calls Today */}
        <div className="rounded-xl border border-slate-100 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-slate-500">Total Calls Today</h3>
            <PhoneCall className="h-4 w-4 text-slate-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-slate-900">1,248</span>
            <span className="flex items-center text-sm font-medium text-emerald-600">
              <TrendingUp className="mr-1 h-3 w-3" />
              12%
            </span>
          </div>
        </div>

        {/* Card 2: Active Live Calls */}
        <div className="rounded-xl border border-slate-100 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-slate-500">Active Live Calls</h3>
            <div className="relative flex h-3 w-3">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex h-3 w-3 rounded-full bg-emerald-500"></span>
            </div>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-slate-900">42</span>
            <span className="text-sm font-medium text-slate-500">agents dialing</span>
          </div>
        </div>

        {/* Card 3: Average Call Duration */}
        <div className="rounded-xl border border-slate-100 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-slate-500">Avg Call Duration</h3>
            <Clock className="h-4 w-4 text-slate-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-slate-900">2m 14s</span>
          </div>
        </div>

        {/* Card 4: Token Savings */}
        <div className="rounded-xl border border-slate-100 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-slate-500">Token Savings</h3>
            <PiggyBank className="h-4 w-4 text-indigo-500" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-slate-900">$84.50</span>
            <span className="text-sm font-medium text-slate-500">via local models</span>
          </div>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
        {/* Left Column: Chart Placeholder */}
        <div className="lg:col-span-2 flex flex-col rounded-xl border border-slate-100 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold text-slate-900">Live Call Activity</h2>
            <button className="text-sm font-medium text-indigo-600 hover:text-indigo-700">View Report</button>
          </div>
          <div className="flex flex-1 items-center justify-center rounded-lg border border-dashed border-slate-200 bg-slate-50 min-h-[300px]">
            <div className="text-center">
              <BarChart3 className="mx-auto h-8 w-8 text-slate-400 mb-2" />
              <p className="text-sm font-medium text-slate-500">Chart data visualization will load here</p>
            </div>
          </div>
        </div>

        {/* Right Column: Recent Dispositions */}
        <div className="flex flex-col rounded-xl border border-slate-100 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900 mb-6">Recent Dispositions</h2>
          <div className="flex-1 space-y-4">
            
            {/* Disposition Item */}
            <div className="flex items-start gap-4 pb-4 border-b border-slate-100 last:border-0">
              <div className="mt-1 rounded-full bg-emerald-100 p-1.5">
                <CheckCircle2 className="h-4 w-4 text-emerald-600" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-slate-900">Interested in Tata Solar</p>
                <p className="text-xs text-slate-500">+91 98765 43210 • 2 mins ago</p>
              </div>
            </div>

            {/* Disposition Item */}
            <div className="flex items-start gap-4 pb-4 border-b border-slate-100 last:border-0">
              <div className="mt-1 rounded-full bg-amber-100 p-1.5">
                <Voicemail className="h-4 w-4 text-amber-600" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-slate-900">Voicemail Left</p>
                <p className="text-xs text-slate-500">+91 99887 76655 • 5 mins ago</p>
              </div>
            </div>

            {/* Disposition Item */}
            <div className="flex items-start gap-4 pb-4 border-b border-slate-100 last:border-0">
              <div className="mt-1 rounded-full bg-indigo-100 p-1.5">
                <CalendarClock className="h-4 w-4 text-indigo-600" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-slate-900">Callback Scheduled</p>
                <p className="text-xs text-slate-500">+91 91234 56789 • 12 mins ago</p>
              </div>
            </div>

            {/* Disposition Item */}
            <div className="flex items-start gap-4 pb-4 border-b border-slate-100 last:border-0">
              <div className="mt-1 rounded-full bg-emerald-100 p-1.5">
                <CheckCircle2 className="h-4 w-4 text-emerald-600" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-slate-900">Pricing Quote Sent</p>
                <p className="text-xs text-slate-500">+91 93456 78901 • 15 mins ago</p>
              </div>
            </div>

          </div>
          <button className="mt-4 w-full rounded-md bg-slate-50 px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 transition-colors">
            View All Activity
          </button>
        </div>
      </div>
    </div>
  );
}
