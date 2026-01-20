import React, { useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { User, Bot, ExternalLink } from 'lucide-react';

const ChatWindow = ({ messages = [] }) => {
    const scrollRef = useRef(null);

    // Force scroll to bottom whenever messages change
    const scrollToBottom = () => {
        if (scrollRef.current) {
            scrollRef.current.scrollTo({
                top: scrollRef.current.scrollHeight,
                behavior: 'smooth'
            });
        }
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    // Additional effect to scroll when content might be streaming or loading
    useEffect(() => {
        const timer = setTimeout(scrollToBottom, 100);
        return () => clearTimeout(timer);
    }, [messages]);

    const renderSources = (sources) => {
        if (!sources || sources.length === 0) return null;

        return (
            <div className="sources-container" style={{
                marginTop: '1.5rem',
                padding: '1rem',
                background: 'var(--glass-bg)',
                borderRadius: '12px',
                border: '1px solid var(--border)',
                fontSize: '0.9rem'
            }}>
                <div style={{ fontWeight: 600, marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--primary)' }}>
                    <ExternalLink size={16} />
                    <span>Recommended Reading</span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    {sources.map((source, idx) => {
                        const urlMatch = source.match(/\((https?:\/\/[^\s)]+)\)/);
                        const url = urlMatch ? urlMatch[1] : null;
                        const title = urlMatch ? source.replace(urlMatch[0], '').trim() : source;

                        return (
                            <div key={idx} style={{ color: 'var(--text-muted)', display: 'flex', alignItems: 'flex-start', gap: '6px' }}>
                                <span style={{ color: 'var(--primary)', marginTop: '2px' }}>•</span>
                                {url ? (
                                    <a href={url} target="_blank" rel="noopener noreferrer" style={{ color: 'inherit', textDecoration: 'none', transition: 'color 0.2s' }} onMouseEnter={(e) => e.target.style.color = 'var(--primary)'} onMouseLeave={(e) => e.target.style.color = 'inherit'}>
                                        {title || url}
                                    </a>
                                ) : (
                                    <span>{source}</span>
                                )}
                            </div>
                        );
                    })}
                </div>
            </div>
        );
    };

    return (
        <div className="chat-content" ref={scrollRef}>
            {messages.length > 0 ? (
                messages.map((msg, idx) => (
                    <div key={idx} className="message-row" style={{ animation: 'fadeIn 0.4s ease forwards' }}>
                        <div className={`message-avatar ${msg.role === 'user' ? 'user-avatar' : 'assistant-avatar'}`} style={{
                            boxShadow: msg.role === 'assistant' ? '0 0 15px var(--primary-glow)' : 'none'
                        }}>
                            {msg.role === 'user' ? <User size={20} color="white" /> : <Bot size={20} color="white" />}
                        </div>
                        <div className="message-content">
                            <div style={{
                                fontWeight: 600,
                                fontSize: '0.8rem',
                                textTransform: 'uppercase',
                                letterSpacing: '0.05em',
                                marginBottom: '0.5rem',
                                opacity: 0.5
                            }}>
                                {msg.role === 'user' ? 'You' : 'Assistant'}
                            </div>
                            <ReactMarkdown
                                remarkPlugins={[remarkGfm]}
                                components={{
                                    a: ({ node, ...props }) => <a {...props} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--primary)', fontWeight: 500 }} />,
                                    p: ({ node, ...props }) => <p {...props} style={{ marginBottom: '1rem' }} />
                                }}
                            >
                                {msg.content}
                            </ReactMarkdown>
                            {renderSources(msg.sources)}
                        </div>
                    </div>
                ))
            ) : (
                <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', color: 'var(--text-muted)', opacity: 0.4 }}>
                    <div style={{
                        width: '80px',
                        height: '80px',
                        background: 'var(--glass-bg)',
                        borderRadius: '24px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        marginBottom: '2rem',
                        border: '1px solid var(--border)'
                    }}>
                        <Bot size={40} strokeWidth={1.5} style={{ margin: 'auto' }} />
                    </div>
                    <h2 style={{ fontWeight: 600, fontSize: '1.5rem', color: 'var(--text-main)', marginBottom: '0.5rem' }}>Your Technical Partner</h2>
                    <p style={{ maxWidth: '400px', textAlign: 'center', lineHeight: 1.6 }}>
                        Ask me anything about our SOPs or complex troubleshooting challenges. I'm here to help you solve issues faster.
                    </p>
                </div>
            )}
        </div>
    );
};

export default ChatWindow;
