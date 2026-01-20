import React from 'react';
import { motion } from 'framer-motion';

const ThinkingLoader = () => {
    return (
        <div className="message-row" style={{ opacity: 0.7 }}>
            <div className="message-avatar assistant-avatar" style={{ background: 'var(--text-muted)' }}>
                <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                >
                    <div style={{ width: '12px', height: '12px', border: '2px solid white', borderTopColor: 'transparent', borderRadius: '50%' }} />
                </motion.div>
            </div>
            <div className="message-content" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <span style={{ fontSize: '0.875rem', fontWeight: 500, color: 'var(--text-muted)' }}>Thinking</span>
                <motion.span
                    animate={{ opacity: [0, 1, 0] }}
                    transition={{ duration: 1.5, repeat: Infinity, times: [0, 0.5, 1] }}
                >
                    .
                </motion.span>
                <motion.span
                    animate={{ opacity: [0, 1, 0] }}
                    transition={{ duration: 1.5, repeat: Infinity, times: [0, 0.5, 1], delay: 0.2 }}
                >
                    .
                </motion.span>
                <motion.span
                    animate={{ opacity: [0, 1, 0] }}
                    transition={{ duration: 1.5, repeat: Infinity, times: [0, 0.5, 1], delay: 0.4 }}
                >
                    .
                </motion.span>
            </div>
        </div>
    );
};

export default ThinkingLoader;
