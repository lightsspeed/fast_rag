import { useState, useCallback, useRef, useEffect } from 'react';
import type { ChatMessage, ChatConversation, SourceCitation } from '@/types/chat';
import { api, type Message as ApiMessage } from '@/services/api';

export function useChat() {
  const [conversations, setConversations] = useState<ChatConversation[]>(() => {
    try {
      const saved = localStorage.getItem('chat_conversations');
      if (saved) {
        return JSON.parse(saved, (key, value) => {
          if (key === 'createdAt' || key === 'updatedAt' || key === 'timestamp') {
            return new Date(value);
          }
          return value;
        });
      }
    } catch (e) {
      console.error('Failed to parse conversations from localStorage', e);
    }
    return [{
      id: '1',
      title: 'New conversation',
      messages: [],
      createdAt: new Date(),
      updatedAt: new Date(),
    }];
  });

  const [activeConversationId, setActiveConversationId] = useState(() => {
    return localStorage.getItem('chat_active_id') || '1';
  });

  // Persist conversations
  useEffect(() => {
    localStorage.setItem('chat_conversations', JSON.stringify(conversations));
  }, [conversations]);

  // Persist active ID
  useEffect(() => {
    localStorage.setItem('chat_active_id', activeConversationId);
  }, [activeConversationId]);
  const [isLoading, setIsLoading] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  const stopGeneration = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  }, []);

  const activeConversation = conversations.find((c) => c.id === activeConversationId);
  const messages = activeConversation?.messages || [];

  const sendMessage = useCallback(async (content: string, images?: string[], skipAddUser?: boolean) => {
    // Cancel any ongoing request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content,
      timestamp: new Date(),
      images,
    };

    if (!skipAddUser) {
      setConversations((prev) =>
        prev.map((conv) => {
          if (conv.id === activeConversationId) {
            const isFirstMessage = conv.messages.length === 0;
            return {
              ...conv,
              messages: [...conv.messages, userMessage],
              title: isFirstMessage ? 'Generating title...' : conv.title,
              updatedAt: new Date(),
            };
          }
          return conv;
        })
      );
    }

    setIsLoading(true);

    // Create assistant message placeholder
    const assistantMessageId = `assistant-${Date.now()}`;
    let assistantContent = '';
    let assistantSources: SourceCitation[] = [];

    const assistantMessage: ChatMessage = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      sources: [],
    };

    // Add empty assistant message
    setConversations((prev) =>
      prev.map((conv) =>
        conv.id === activeConversationId
          ? {
            ...conv,
            messages: [...conv.messages, assistantMessage],
            updatedAt: new Date(),
          }
          : conv
      )
    );

    // Prepare chat history for API
    const chatHistory: ApiMessage[] = [];
    const conv = conversations.find((c) => c.id === activeConversationId);
    if (conv) {
      // Get all messages except the one we just added
      const historyMessages = conv.messages.slice(0, -1);
      for (const msg of historyMessages) {
        chatHistory.push({
          role: msg.role,
          content: msg.content,
        });
      }
    }

    // Create abort controller for this request (not really used for WS, but good for cleanup)
    abortControllerRef.current = new AbortController();

    try {
      await api.streamQuery(
        content,
        activeConversationId,
        images,
        // onMetadata
        (metadata) => {
          // Convert backend sources to frontend format
          const sources: SourceCitation[] = metadata.sources.map((source, idx) => ({
            id: source.id || `source-${idx}`,
            documentName: source.documentName || 'Unknown Document',
            excerpt: source.excerpt || '',
            confidence: source.confidence !== undefined ? source.confidence : 0.9,
            title: source.title,
            isWeb: source.isWeb,
          }));
          assistantSources = sources;

          // Update message with sources
          setConversations((prev) =>
            prev.map((conv) =>
              conv.id === activeConversationId
                ? {
                  ...conv,
                  messages: conv.messages.map((msg) =>
                    msg.id === assistantMessageId
                      ? { ...msg, sources }
                      : msg
                  ),
                }
                : conv
            )
          );
        },
        // onContent
        (text) => {
          if (!assistantContent) {
            // Start the deliberate 2-second check timer when the first token arrives
            setTimeout(() => {
              setConversations((prev) =>
                prev.map((conv) => {
                  if (conv.id !== activeConversationId) return conv;

                  const isPlaceholder = ['Generating title...', 'New Chat', 'New conversation'].includes(conv.title);
                  if (!isPlaceholder) return conv;

                  // Perform the "proper check" on what we have so far
                  const h1Match = assistantContent.match(/^#\s*(?:Title:\s*)?([^*#\n]{3,60})/i) ||
                    assistantContent.match(/Title:\s*(?:\*\*)?([^*:\n]{3,60})/i);

                  if (h1Match?.[1]) {
                    return { ...conv, title: h1Match[1].trim() };
                  }
                  return conv;
                })
              );
            }, 2000);
          }

          assistantContent += text;

          // Update message content in real-time
          setConversations((prev) =>
            prev.map((conv) => {
              if (conv.id !== activeConversationId) return conv;

              return {
                ...conv,
                messages: conv.messages.map((msg) =>
                  msg.id === assistantMessageId
                    ? { ...msg, content: assistantContent }
                    : msg
                ),
                updatedAt: new Date(),
              };
            })
          );
        },
        // onComplete
        () => {
          setIsLoading(false);
          abortControllerRef.current = null;

          // Final Resolution Fallback (if timer didn't catch it or stream was too short)
          setTimeout(() => {
            setConversations((prev) =>
              prev.map((conv) => {
                if (conv.id !== activeConversationId) return conv;

                const isPlaceholder = ['Generating title...', 'New Chat', 'New conversation'].includes(conv.title);
                if (!isPlaceholder) return conv;

                const finalMatch = assistantContent.match(/^#\s*(?:Title:\s*)?([^*#\n]{3,60})/i) ||
                  assistantContent.match(/Title:\s*(?:\*\*)?([^*:\n]{3,60})/i);

                if (finalMatch?.[1]) return { ...conv, title: finalMatch[1].trim() };

                const words = content.trim().split(/\s+/);
                const fallback = words.slice(0, 3).join(' ') + (words.length > 3 ? '...' : '');
                return { ...conv, title: fallback || 'New Chat' };
              })
            );
          }, 500); // Small extra buffer on complete
        },
        // onError
        (error) => {
          if (error.message === 'Aborted') {
            console.log('Query aborted by user');
            // Update message to show it was stopped
            setConversations((prev) =>
              prev.map((conv) =>
                conv.id === activeConversationId
                  ? {
                    ...conv,
                    messages: conv.messages.map((msg) =>
                      msg.id === assistantMessageId
                        ? {
                          ...msg,
                          content: assistantContent
                            ? `${assistantContent}\n\n*Generation stopped by user.*`
                            : "*Generation stopped by user.*"
                        }
                        : msg
                    ),
                  }
                  : conv
              )
            );
            return;
          }
          console.error('WebSocket error:', error);

          // Update message with error
          setConversations((prev) =>
            prev.map((conv) =>
              conv.id === activeConversationId
                ? {
                  ...conv,
                  messages: conv.messages.map((msg) =>
                    msg.id === assistantMessageId
                      ? {
                        ...msg,
                        content: `Error: ${error.message}. Please make sure the backend server is running on port 8000.`
                      }
                      : msg
                  ),
                }
                : conv
            )
          );

          setIsLoading(false);
          abortControllerRef.current = null;
        },
        abortControllerRef.current?.signal
      );
    } catch (error) {
      console.error('Failed to send message:', error);
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  }, [activeConversationId, conversations]);

  const createNewConversation = useCallback(() => {
    const newConv: ChatConversation = {
      id: Date.now().toString(),
      title: 'New conversation',
      messages: [],
      createdAt: new Date(),
      updatedAt: new Date(),
      isPinned: false,
    };
    setConversations((prev) => [newConv, ...prev]);
    setActiveConversationId(newConv.id);
  }, []);

  const deleteConversation = useCallback((id: string) => {
    setConversations((prev) => {
      const filtered = prev.filter((c) => c.id !== id);
      // If we deleted the active conversation, switch to another one
      if (id === activeConversationId && filtered.length > 0) {
        setActiveConversationId(filtered[0].id);
      } else if (filtered.length === 0) {
        // Create a new conversation if all are deleted
        const newConv: ChatConversation = {
          id: Date.now().toString(),
          title: 'New conversation',
          messages: [],
          createdAt: new Date(),
          updatedAt: new Date(),
          isPinned: false,
        };
        setActiveConversationId(newConv.id);
        return [newConv];
      }
      return filtered;
    });
  }, [activeConversationId]);

  const renameConversation = useCallback((id: string, newTitle: string) => {
    setConversations((prev) =>
      prev.map((conv) =>
        conv.id === id
          ? { ...conv, title: newTitle, updatedAt: new Date() }
          : conv
      )
    );
  }, []);

  const togglePinConversation = useCallback((id: string) => {
    setConversations((prev) =>
      prev.map((conv) =>
        conv.id === id
          ? { ...conv, isPinned: !conv.isPinned, updatedAt: new Date() }
          : conv
      )
    );
  }, []);

  const searchMessages = useCallback((query: string) => {
    if (!query.trim()) return [];

    const results: { conversation: ChatConversation; message: ChatMessage }[] = [];

    conversations.forEach((conv) => {
      conv.messages.forEach((msg) => {
        if (msg.content.toLowerCase().includes(query.toLowerCase())) {
          results.push({ conversation: conv, message: msg });
        }
      });
    });

    return results;
  }, [conversations]);

  const clearMessages = useCallback(() => {
    setConversations((prev) =>
      prev.map((conv) =>
        conv.id === activeConversationId
          ? { ...conv, messages: [], updatedAt: new Date() }
          : conv
      )
    );
  }, [activeConversationId]);

  const updateMessageFeedback = useCallback((messageId: string, feedback: 'up' | 'down' | null) => {
    setConversations((prev) =>
      prev.map((conv) =>
        conv.id === activeConversationId
          ? {
            ...conv,
            messages: conv.messages.map((msg) =>
              msg.id === messageId ? { ...msg, feedback } : msg
            ),
            updatedAt: new Date(),
          }
          : conv
      )
    );
  }, [activeConversationId]);

  const editMessage = useCallback(async (messageId: string, newContent: string, images?: string[]) => {
    // Find the message index
    const conv = conversations.find((c) => c.id === activeConversationId);
    if (!conv) return;

    const messageIndex = conv.messages.findIndex((m) => m.id === messageId);
    if (messageIndex === -1) return;

    // Remove all messages from the edited one onwards
    const updatedMessages = conv.messages.slice(0, messageIndex);

    // Add the edited message
    const editedMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: newContent,
      timestamp: new Date(),
      images,
    };

    const isFirstMessage = messageIndex === 0;

    setConversations((prev) =>
      prev.map((c) =>
        c.id === activeConversationId
          ? {
            ...c,
            messages: [...updatedMessages, editedMessage],
            updatedAt: new Date(),
            title: isFirstMessage ? 'Generating title...' : c.title
          }
          : c
      )
    );

    // Send the edited message, skipping the second add
    await sendMessage(newContent, images, true);
  }, [activeConversationId, conversations, sendMessage]);

  // Sort conversations: pinned first, then by updatedAt
  const sortedConversations = [...conversations].sort((a, b) => {
    if (a.isPinned && !b.isPinned) return -1;
    if (!a.isPinned && b.isPinned) return 1;
    return b.updatedAt.getTime() - a.updatedAt.getTime();
  });

  return {
    messages,
    conversations: sortedConversations,
    activeConversationId,
    isLoading,
    sendMessage,
    stopGeneration,
    createNewConversation,
    setActiveConversationId,
    searchMessages,
    clearMessages,
    updateMessageFeedback,
    editMessage,
    deleteConversation,
    renameConversation,
    togglePinConversation,
  };
}
