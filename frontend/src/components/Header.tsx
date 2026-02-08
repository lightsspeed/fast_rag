import { Moon, Sun, Sparkles, Menu } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ITSupportNavbar } from './ITSupportNavbar';

interface HeaderProps {
  theme: 'light' | 'dark';
  onToggleTheme: () => void;
  onSelectIssue: (query: string) => void;
  onToggleMenu?: () => void;
}

export function Header({ theme, onToggleTheme, onSelectIssue, onToggleMenu }: HeaderProps) {
  return (
    <header className="h-14 border-b border-border bg-card/80 backdrop-blur-xl sticky top-0 z-50 flex items-center px-4 md:px-6 gap-4">
      {/* Mobile Menu Toggle */}
      <Button
        variant="ghost"
        size="icon"
        onClick={onToggleMenu}
        className="md:hidden h-9 w-9 text-muted-foreground hover:text-foreground shrink-0"
      >
        <Menu className="w-5 h-5" />
      </Button>

      {/* Logo */}
      <div className="flex items-center gap-3 shrink-0">
        <div className="w-8 h-8 rounded-lg overflow-hidden flex items-center justify-center shadow-lg shadow-primary/20 bg-background border border-border">
          <img src="/downloadjio.png" alt="Logo" className="w-full h-full object-contain" />
        </div>
        <span className="font-semibold text-foreground hidden sm:block">IntelliQuery</span>
      </div>

      {/* Navbar - centered */}
      <div className="flex-1 flex justify-center overflow-x-auto scrollbar-hide">
        <ITSupportNavbar onSelectIssue={onSelectIssue} />
      </div>

      {/* Theme toggle */}
      <Button
        variant="ghost"
        size="icon"
        onClick={onToggleTheme}
        className="h-9 w-9 text-muted-foreground hover:text-foreground shrink-0"
      >
        {theme === 'light' ? (
          <Moon className="w-4 h-4" />
        ) : (
          <Sun className="w-4 h-4" />
        )}
      </Button>
    </header>
  );
}
