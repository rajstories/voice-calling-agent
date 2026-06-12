import { ChevronRight, ChevronsUpDown, User } from "lucide-react";

export default function Header() {
  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-slate-200 bg-white px-6">
      {/* Breadcrumb Trail */}
      <div className="flex items-center text-sm text-slate-500 font-medium">
        <span className="hover:text-slate-900 cursor-pointer">Vobiz AI</span>
        <ChevronRight className="mx-2 h-4 w-4" />
        <span className="text-slate-900">Dashboard</span>
      </div>

      {/* Right Side: Tenant Switcher & Profile */}
      <div className="flex items-center gap-4">
        {/* Tenant Switcher (Visual placeholder) */}
        <div className="flex items-center gap-2 rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50 cursor-pointer transition-colors">
          <div className="h-5 w-5 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-700 font-bold text-xs">
            U
          </div>
          <span>UPM Consultancy</span>
          <ChevronsUpDown className="ml-2 h-4 w-4 text-slate-400" />
        </div>

        {/* User Profile Avatar */}
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-100 border border-slate-200 cursor-pointer hover:bg-slate-200 transition-colors">
          <User className="h-5 w-5 text-slate-600" />
        </div>
      </div>
    </header>
  );
}
