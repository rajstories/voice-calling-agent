import Link from "next/link";
import { 
  LayoutDashboard, 
  Users, 
  BookOpen, 
  Network, 
  PhoneCall 
} from "lucide-react";

const navigation = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Tenant Hub", href: "#", icon: Users },
  { name: "Knowledge Vault", href: "#", icon: BookOpen },
  { name: "Graphify Canvas", href: "#", icon: Network },
  { name: "Live Calls", href: "#", icon: PhoneCall },
];

export default function Sidebar() {
  return (
    <div className="flex h-full w-64 flex-col bg-slate-950 border-r border-slate-800">
      <div className="flex h-16 shrink-0 items-center px-6">
        <div className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-indigo-600 flex items-center justify-center">
            <Network className="h-5 w-5 text-white" />
          </div>
          Vobiz AI
        </div>
      </div>
      <div className="flex flex-1 flex-col overflow-y-auto pt-5 pb-4">
        <nav className="flex-1 space-y-1 px-3">
          {navigation.map((item) => {
            const Icon = item.icon;
            return (
              <Link
                key={item.name}
                href={item.href}
                className="group flex items-center rounded-md px-3 py-2 text-sm font-medium text-slate-300 hover:bg-slate-900 hover:text-white transition-colors"
              >
                <Icon
                  className="mr-3 h-5 w-5 shrink-0 text-slate-400 group-hover:text-white transition-colors"
                  aria-hidden="true"
                />
                {item.name}
              </Link>
            );
          })}
        </nav>
      </div>
    </div>
  );
}
