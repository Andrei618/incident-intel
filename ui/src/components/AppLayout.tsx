import { Moon, Sun } from "lucide-react";
import { NavLink, Outlet, Link } from "react-router-dom";
import { useTheme } from "@/components/ThemeProvider";
import { Button } from "@/components/ui/button";
import { Toaster } from "@/components/ui/sonner";

export function AppLayout() {
  const { theme, toggleTheme } = useTheme();
  const icon = theme === "dark" ? <Sun /> : <Moon />;
  const navClass = ({ isActive }: { isActive: boolean }) =>
    isActive
      ? "font-semibold text-foreground"
      : "text-muted-foreground hover:text-foreground transition-colors";

  return (
    <div className="min-h-screen flex flex-col">
      <header className="flex items-center gap-3 px-3 sm:gap-6 sm:px-6 py-3 border-b bg-background">
        <Link
          to="/"
          className="font-semibold text-foreground whitespace-nowrap shrink-0"
        >
          Incident Intel
        </Link>
        <nav className="flex items-center gap-2 sm:gap-4 flex-1 overflow-x-auto">
          <NavLink to="/chat" className={navClass}>
            Chat
          </NavLink>
          <NavLink to="/tickets" className={navClass}>
            Tickets
          </NavLink>
          <NavLink to="/search" className={navClass}>
            Search
          </NavLink>
          <NavLink to="/documents" className={navClass}>
            Documents
          </NavLink>
        </nav>

        <Button
          onClick={toggleTheme}
          variant="ghost"
          size="icon"
          className="shrink-0 ml-auto"
          aria-label="Toggle theme"
        >
          {icon}
        </Button>
      </header>
      <main className="flex flex-col flex-1 max-w-5xl mx-auto w-full px-6 py-8">
        <Outlet />
      </main>
      <Toaster />
    </div>
  );
}
