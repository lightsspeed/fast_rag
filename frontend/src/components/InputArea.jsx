import React, { useState, useRef } from 'react';
import { Send, Paperclip, X, Image as ImageIcon } from 'lucide-react';

const InputArea = ({ onSend, isLoading }) => {
    const [input, setInput] = useState('');
    const [screenshot, setScreenshot] = useState(null);
    const fileInputRef = useRef(null);

    const handleSend = () => {
        if ((input.trim() || screenshot) && !isLoading) {
            onSend(input, screenshot);
            setInput('');
            setScreenshot(null);
        }
    };

    const handleFileChange = (e) => {
        const file = e.target.files[0];
        if (file && file.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = (event) => {
                setScreenshot({
                    file: file,
                    url: event.target.result
                });
            };
            reader.readAsDataURL(file);
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div className="input-section">
            <div className="input-container">
                <div style={{ display: 'flex', flexDirection: 'column', flex: 1 }}>
                    {screenshot && (
                        <div style={{ padding: '0.5rem', display: 'flex', gap: '8px' }}>
                            <div style={{ position: 'relative', width: '60px', height: '60px', borderRadius: '8px', overflow: 'hidden', border: '1px solid var(--border)' }}>
                                <img src={screenshot.url} alt="preview" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                                <button
                                    onClick={() => setScreenshot(null)}
                                    style={{ position: 'absolute', top: '2px', right: '2px', background: 'rgba(0,0,0,0.5)', borderRadius: '50%', width: '16px', height: '16px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                                >
                                    <X size={10} color="white" />
                                </button>
                            </div>
                        </div>
                    )}
                    <textarea
                        className="chat-textarea"
                        placeholder="Describe the issue or ask a question..."
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        rows={1}
                        style={{ height: 'auto' }}
                    />
                </div>

                <div className="input-actions">
                    <input
                        type="file"
                        ref={fileInputRef}
                        onChange={handleFileChange}
                        accept="image/*"
                        style={{ display: 'none' }}
                    />
                    <button
                        className="action-btn"
                        onClick={() => fileInputRef.current.click()}
                        title="Add screenshot"
                    >
                        <Paperclip size={20} />
                    </button>
                    <button
                        className={`action-btn send-btn ${(!input.trim() && !screenshot) || isLoading ? 'opacity-50' : ''}`}
                        onClick={handleSend}
                        disabled={(!input.trim() && !screenshot) || isLoading}
                    >
                        <Send size={18} />
                    </button>
                </div>
            </div>
            <div className="footer-disclaimer">
                RAG Assistant can make mistakes. Verify critical steps with official SOPs.
            </div>
        </div>
    );
};

export default InputArea;
