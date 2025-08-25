import { Home, Building2, Briefcase, Users, Activity, BarChart3, Settings } from "lucide-react";
import { NavLink } from "react-router-dom";
import { cn } from "@/lib/utils";

const navigationItems = [
  { name: "Home", href: "/dashboard", icon: Home },
  { name: "Departments", href: "/departments", icon: Building2 },
  { name: "Jobs", href: "/jobs", icon: Briefcase },
  { name: "Candidates", href: "/candidates", icon: Users },
  { name: "Activity", href: "/activity", icon: Activity },
  { name: "Reports", href: "/reports", icon: BarChart3 },
  { name: "Settings", href: "/settings", icon: Settings },
];

interface SidebarProps {
  isCollapsed: boolean;
  onExpandRequest: () => void;
}

export function Sidebar({ isCollapsed, onExpandRequest }: SidebarProps) {
  return (
    <div className={cn(
      "fixed left-0 top-16 bottom-0 bg-sidebar border-r border-sidebar-border transition-all duration-300",
      isCollapsed ? "w-16" : "w-64"
    )}>
      <nav className="p-4">
        <ul className="space-y-2">
          {navigationItems.map((item) => {
            const Icon = item.icon;
            return (
              <li key={item.name}>
                <NavLink
                  to={item.href}
                  onClick={() => {
                    if (isCollapsed) {
                      onExpandRequest();
                    }
                  }}
                  className={({ isActive }) =>
                    cn(
                      "flex items-center rounded-lg text-sm font-medium transition-all duration-200",
                      isCollapsed ? "justify-center px-3 py-2" : "space-x-3 px-3 py-2",
                      isActive
                        ? "bg-primary text-primary-foreground shadow-sm"
                        : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                    )
                  }
                  title={isCollapsed ? item.name : undefined}
                >
                  <Icon className="h-5 w-5 flex-shrink-0" />
                  {!isCollapsed && <span>{item.name}</span>}
                </NavLink>
              </li>
            );
          })}
        </ul>
      </nav>
    </div>
  );
}