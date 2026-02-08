import { useState } from 'react';
import { TypingIndicator } from './TypingIndicator';
import { User, Sparkles, ThumbsUp, ThumbsDown, Copy, Check, Pencil, Library } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { cn } from '@/lib/utils';
import { SourceCard } from './SourceCard';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import type { ChatMessage as ChatMessageType, SourceCitation } from '@/types/chat';

interface ChatMessageProps {
  message: ChatMessageType;
  isStreaming?: boolean;
  onEdit?: (message: ChatMessageType) => void;
  onFeedback?: (messageId: string, feedback: 'up' | 'down' | null) => void;
  onViewSources?: (sources: SourceCitation[]) => void;
}

const CodeBlock = ({ children, isUser }: { children: any, isUser: boolean }) => {
  const [copied, setCopied] = useState(false);
  const codeString = String(children).replace(/\n$/, '');

  const handleCopy = async () => {
    await navigator.clipboard.writeText(codeString);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="group relative my-4">
      <code
        className={cn(
          "font-mono text-[14px] font-medium block p-4 rounded-xl border border-border/50 shadow-sm overflow-x-auto",
          isUser
            ? "text-chat-user-foreground bg-black/5"
            : "text-foreground bg-muted/50 dark:bg-muted/20"
        )}
      >
        {children}
      </code>
      {!isUser && (
        <Button
          variant="ghost"
          size="icon"
          className="absolute top-3 right-3 h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity bg-background/80 backdrop-blur-sm border border-border/50 hover:bg-background shadow-sm"
          onClick={handleCopy}
        >
          {copied ? (
            <Check className="h-4 w-4 text-green-500" />
          ) : (
            <Copy className="h-4 w-4 text-muted-foreground" />
          )}
        </Button>
      )}
    </div>
  );
};

export function ChatMessage({ message, isStreaming, onEdit, onFeedback, onViewSources }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);
  const { toast } = useToast();

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    toast({
      description: "Message copied to clipboard",
    });
    setTimeout(() => setCopied(false), 2000);
  };

  const handleFeedback = (type: 'up' | 'down') => {
    const newFeedback = message.feedback === type ? null : type;
    onFeedback?.(message.id, newFeedback);

    if (newFeedback) {
      toast({
        description: newFeedback === 'up'
          ? "Thanks for the positive feedback! 👍"
          : "Thanks for the feedback. We'll improve! 👎",
      });
    }
  };

  return (
    <div
      className={cn(
        "flex gap-3 animate-message-in",
        isUser ? "flex-row-reverse" : "flex-row"
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          "flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center",
          isUser ? "bg-primary" : "bg-accent"
        )}
      >
        {isUser ? (
          <User className="w-4 h-4 text-primary-foreground" />
        ) : (
          <Sparkles className="w-4 h-4 text-accent-foreground" />
        )}
      </div>

      {/* Content or Loading Indicator */}
      <div
        className={cn(
          "flex flex-col",
          isUser ? "items-end max-w-[70%]" : "items-start w-full max-w-full"
        )}
      >
        {isStreaming ? (
          <div className="bg-card border border-border rounded-xl p-4 shadow-sm">
            <TypingIndicator />
          </div>
        ) : (
          <div
            className={cn(
              "rounded-3xl bg-card text-card-foreground border-2 border-primary/20 shadow-sm shadow-primary/5",
              isUser
                ? "px-5 py-3 flex flex-col gap-3 min-h-[3rem]"
                : message.isStopped
                  ? "px-6 py-4 max-w-fit text-center"
                  : "p-8 md:p-12"
            )}
          >
            {/* Display images for user messages - ABOVE the text */}
            {isUser && message.images && message.images.length > 0 && (
              <div className="flex flex-wrap gap-2 w-full">
                {message.images.map((img, idx) => (
                  <img
                    key={idx}
                    src={img}
                    alt={`Uploaded image ${idx + 1}`}
                    className="max-w-full h-auto rounded-lg border border-border/50 cursor-pointer hover:opacity-90 transition-opacity"
                    style={{ maxHeight: '300px', objectFit: 'contain' }}
                  />
                ))}
              </div>
            )}

            <div className={cn(
              "w-full max-w-none",
              isUser
                ? "text-chat-user-foreground"
                : "text-foreground"
            )}>
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  h1: ({ ...props }) => (
                    <h1 className="text-3xl font-bold mb-6 mt-2 tracking-tight text-foreground" {...props} />
                  ),
                  h2: ({ ...props }) => (
                    <h2 className="text-2xl font-bold mb-4 mt-8 tracking-tight text-foreground/90" {...props} />
                  ),
                  h3: ({ ...props }) => (
                    <h3 className="text-lg font-semibold mb-3 mt-6 text-foreground/90" {...props} />
                  ),
                  p: ({ ...props }) => (
                    <p className={cn("text-base leading-7 text-foreground/80 font-normal", isUser ? "mb-0" : "mb-4")} {...props} />
                  ),
                  a: ({ ...props }) => (
                    <a
                      {...props}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary hover:underline font-medium ml-0.5"
                    />
                  ),
                  ul: ({ ...props }) => (
                    <ul className="list-disc pl-6 mb-4 space-y-2 text-[15px] text-foreground/80" {...props} />
                  ),
                  ol: ({ ...props }) => (
                    <ol className="list-decimal pl-6 mb-4 space-y-2 text-[15px] text-foreground/80" {...props} />
                  ),
                  li: ({ ...props }) => (
                    <li className="pl-1" {...props} />
                  ),
                  blockquote: ({ ...props }) => (
                    <blockquote className="border-l-4 border-primary/30 pl-4 italic my-4 text-muted-foreground" {...props} />
                  ),
                  code: ({ node, ...props }) => {
                    const { inline, children, ...rest } = props as any;
                    const codeString = String(children).replace(/\n$/, '');

                    if (inline) {
                      return (
                        <code
                          {...rest}
                          className={cn(
                            "font-mono text-[14px] font-medium px-1.5 py-0.5 rounded",
                            isUser
                              ? "text-chat-user-foreground bg-black/5"
                              : "text-foreground bg-muted/50 dark:bg-muted/20"
                          )}
                        >
                          {children}
                        </code>
                      );
                    }

                    return <CodeBlock isUser={isUser}>{children}</CodeBlock>;
                  },
                  pre: ({ ...props }) => (
                    <pre className="bg-transparent p-0 m-0 overflow-hidden" {...props} />
                  ),
                  img: ({ node, ...props }) => {
                    const [hasError, setHasError] = useState(false);

                    if (hasError) return null;

                    return (
                      <img
                        {...props}
                        className="rounded-lg max-w-full h-auto my-2 border border-border"
                        onError={() => setHasError(true)}
                      />
                    );
                  }
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          </div>
        )}

        {/* Action buttons - Hide when streaming or stopped */}
        {!isStreaming && !message.isStopped && (
          <div className={cn(
            "flex items-center gap-1 mt-1 px-1",
            isUser ? "flex-row-reverse" : "flex-row"
          )}>
            {/* Copy button - for both */}
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6 text-muted-foreground hover:text-foreground"
              onClick={handleCopy}
            >
              {copied ? (
                <Check className="h-3 w-3 text-green-500" />
              ) : (
                <Copy className="h-3 w-3" />
              )}
            </Button>

            {/* User message: Edit button */}
            {isUser && onEdit && (
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 text-muted-foreground hover:text-foreground"
                onClick={() => onEdit(message)}
              >
                <Pencil className="h-3 w-3" />
              </Button>
            )}

            {/* AI message: Thumbs up/down */}
            {!isUser && (
              <>
                <Button
                  variant="ghost"
                  size="icon"
                  className={cn(
                    "h-6 w-6",
                    message.feedback === 'up'
                      ? "text-green-500 hover:text-green-600"
                      : "text-muted-foreground hover:text-foreground"
                  )}
                  onClick={() => handleFeedback('up')}
                >
                  <ThumbsUp className="h-3 w-3" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className={cn(
                    "h-6 w-6",
                    message.feedback === 'down'
                      ? "text-red-500 hover:text-red-600"
                      : "text-muted-foreground hover:text-foreground"
                  )}
                  onClick={() => handleFeedback('down')}
                >
                  <ThumbsDown className="h-3 w-3" />
                </Button>
              </>
            )}

            {/* Sources button - only for AI with sources */}
            {!isUser && message.sources && message.sources.length > 0 && (
              <Button
                variant="outline"
                size="sm"
                className="ml-auto h-7 gap-1.5 text-xs font-medium border-primary/20 hover:bg-primary/5 hover:border-primary/40 bg-background/50 backdrop-blur-sm"
                onClick={() => onViewSources?.(message.sources!)}
              >
                <Library className="h-3.5 w-3.5 text-primary" />
                Sources
              </Button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
