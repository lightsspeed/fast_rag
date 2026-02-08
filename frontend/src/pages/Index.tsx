import { useState, useCallback } from 'react';
import { Header } from '@/components/Header';
import { Sidebar } from '@/components/Sidebar';
import { ChatArea } from '@/components/ChatArea';
import { CommandPalette } from '@/components/CommandPalette';
import { SourcesSidebar } from '@/components/SourcesSidebar';
import { useChat } from '@/hooks/useChat';
import { useTheme } from '@/hooks/useTheme';
import type { SourceCitation } from '@/types/chat';

const Index = () => {
  const { theme, toggleTheme } = useTheme();
  const {
    messages,
    conversations,
    activeConversationId,
    isLoading,
    sendMessage,
    createNewConversation,
    setActiveConversationId,
    searchMessages,
    updateMessageFeedback,
    editMessage,
    deleteConversation,
    renameConversation,
    togglePinConversation,
    stopGeneration,
  } = useChat();

  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [pendingInput, setPendingInput] = useState('');
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const [activeSources, setActiveSources] = useState<SourceCitation[]>([]);

  const openSearch = () => {
    setCommandPaletteOpen(true);
    setMobileMenuOpen(false);
  };

  const handleSelectIssue = useCallback((query: string) => {
    setPendingInput(query);
    setMobileMenuOpen(false);
  }, []);

  const handleClearPendingInput = useCallback(() => {
    setPendingInput('');
  }, []);

  const handleViewSources = useCallback((sources: SourceCitation[]) => {
    setActiveSources(sources);
    setSourcesOpen(true);
  }, []);

  return (
    <div className="h-screen flex flex-col bg-background">
      {/* Header */}
      <Header
        theme={theme}
        onToggleTheme={toggleTheme}
        onSelectIssue={handleSelectIssue}
        onToggleMenu={() => setMobileMenuOpen(!mobileMenuOpen)}
      />

      {/* Main content */}
      <div className="flex-1 flex min-h-0 relative">
        {/* Sidebar */}
        <Sidebar
          conversations={conversations}
          activeConversationId={activeConversationId}
          onSelectConversation={(id) => {
            setActiveConversationId(id);
            setMobileMenuOpen(false);
          }}
          onNewConversation={() => {
            createNewConversation();
            setMobileMenuOpen(false);
          }}
          onOpenSearch={openSearch}
          isCollapsed={sidebarCollapsed}
          isMobileOpen={mobileMenuOpen}
          onMobileClose={() => setMobileMenuOpen(false)}
          onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
          onDeleteConversation={deleteConversation}
          onRenameConversation={renameConversation}
          onTogglePinConversation={togglePinConversation}
        />

        {/* Chat Area */}
        <ChatArea
          messages={messages}
          isLoading={isLoading}
          onSendMessage={sendMessage}
          externalInput={pendingInput}
          onClearExternalInput={handleClearPendingInput}
          onFeedback={updateMessageFeedback}
          onEditMessage={editMessage}
          onViewSources={handleViewSources}
          onStopGeneration={stopGeneration}
        />
      </div>

      {/* Sources Sidebar */}
      <SourcesSidebar
        isOpen={sourcesOpen}
        onClose={() => setSourcesOpen(false)}
        sources={activeSources}
      />

      {/* Command Palette */}
      <CommandPalette
        open={commandPaletteOpen}
        onOpenChange={setCommandPaletteOpen}
        conversations={conversations}
        onSelectConversation={setActiveConversationId}
        onNewConversation={createNewConversation}
        onToggleTheme={toggleTheme}
        theme={theme}
        searchMessages={searchMessages}
      />
    </div>
  );
};

export default Index;
