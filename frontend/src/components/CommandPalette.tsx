import { useEffect, useState, useCallback } from 'react';
import { Search, MessageSquare, FileText, Moon, Sun, Plus } from 'lucide-react';
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from '@/components/ui/command';
import { ChatConversation, ChatMessage } from '@/types/chat';

interface CommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  conversations: ChatConversation[];
  onSelectConversation: (id: string) => void;
  onNewConversation: () => void;
  onToggleTheme: () => void;
  theme: 'light' | 'dark';
  searchMessages: (query: string) => { conversation: ChatConversation; message: ChatMessage }[];
}

export function CommandPalette({
  open,
  onOpenChange,
  conversations,
  onSelectConversation,
  onNewConversation,
  onToggleTheme,
  theme,
  searchMessages,
}: CommandPaletteProps) {
  const [search, setSearch] = useState('');
  const [searchResults, setSearchResults] = useState<{ conversation: ChatConversation; message: ChatMessage }[]>([]);

  useEffect(() => {
    if (search.length > 2) {
      setSearchResults(searchMessages(search));
    } else {
      setSearchResults([]);
    }
  }, [search, searchMessages]);

  const handleSelect = useCallback((callback: () => void) => {
    callback();
    onOpenChange(false);
    setSearch('');
  }, [onOpenChange]);

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        onOpenChange(!open);
      }
    };

    document.addEventListener('keydown', down);
    return () => document.removeEventListener('keydown', down);
  }, [open, onOpenChange]);

  return (
    <CommandDialog open={open} onOpenChange={onOpenChange}>
      <CommandInput 
        placeholder="Search conversations, messages, or type a command..." 
        value={search}
        onValueChange={setSearch}
      />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>

        {/* Quick Actions */}
        <CommandGroup heading="Quick Actions">
          <CommandItem onSelect={() => handleSelect(onNewConversation)}>
            <Plus className="mr-2 h-4 w-4" />
            <span>New Conversation</span>
          </CommandItem>
          <CommandItem onSelect={() => handleSelect(onToggleTheme)}>
            {theme === 'light' ? (
              <Moon className="mr-2 h-4 w-4" />
            ) : (
              <Sun className="mr-2 h-4 w-4" />
            )}
            <span>Toggle {theme === 'light' ? 'Dark' : 'Light'} Mode</span>
          </CommandItem>
        </CommandGroup>

        <CommandSeparator />

        {/* Search Results */}
        {searchResults.length > 0 && (
          <CommandGroup heading="Search Results">
            {searchResults.slice(0, 5).map((result, idx) => (
              <CommandItem
                key={`${result.conversation.id}-${result.message.id}-${idx}`}
                onSelect={() => handleSelect(() => onSelectConversation(result.conversation.id))}
              >
                <FileText className="mr-2 h-4 w-4" />
                <div className="flex flex-col">
                  <span className="text-sm">{result.conversation.title}</span>
                  <span className="text-xs text-muted-foreground truncate max-w-[300px]">
                    {result.message.content.slice(0, 60)}...
                  </span>
                </div>
              </CommandItem>
            ))}
          </CommandGroup>
        )}

        {/* Recent Conversations */}
        <CommandGroup heading="Recent Conversations">
          {conversations.slice(0, 5).map((conv) => (
            <CommandItem
              key={conv.id}
              onSelect={() => handleSelect(() => onSelectConversation(conv.id))}
            >
              <MessageSquare className="mr-2 h-4 w-4" />
              <span>{conv.title}</span>
            </CommandItem>
          ))}
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}
