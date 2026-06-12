import { Link, useLocation } from "react-router-dom";
import { MessageSquare, Database, Bot } from "lucide-react";

export function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();

  const isActive = (path: string) => location.pathname === path;

  const navItems = [
    { path: "/", label: "Chat", icon: MessageSquare },
    { path: "/memory", label: "Memory", icon: Database },
  ];

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-gray-200 flex flex-col">
        {/* Logo/Header */}
        <div className="h-16 flex items-center px-6 border-b border-gray-200">
          <Bot className="w-5 h-5 text-gray-600 mr-3" />
          <h1 className="text-lg font-semibold text-gray-900">AgentCore</h1>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-4 py-6 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.path);
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                  active
                    ? "bg-gray-100 text-gray-900"
                    : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                }`}
              >
                <Icon className="w-5 h-5 mr-3" />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        <div className="h-full">{children}</div>
      </main>
    </div>
  );
}
