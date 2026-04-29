import { NavLink, Outlet, Link } from "react-router-dom";
import { useTheme } from "./ThemeProvider";
import { Moon, Sun } from "lucide-react";
import { Button } from "./ui/button";

export function AppLayout() {
  const { theme, toggleTheme } = useTheme();
  const icon = theme === "dark" ? <Sun /> : <Moon />;
  const navClass = ({ isActive }: { isActive: boolean }) =>
    isActive 
        ? "font-semibold text-foreground" 
        : "text-muted-foreground hover:text-foreground transition-colors";

  return (
    <div className="min-h-screen flex flex-col">
      <header className="flex items-center gap-6 px-6 py-3 border-b bg-background">
        <Link to="/" className="font-semibold text-foreground">
          Incident Intel
        </Link>
        <nav className="flex items-center gap-4">
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
          className="ml-auto"
          aria-label="Toggle theme"
        >
          {icon}
        </Button>
      </header>
      <main className="flex-1 max-w-5xl mx-auto w-full px-6 py-8">
        <Outlet />
      </main>
    </div>
  );
}
