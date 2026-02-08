import { useEffect, useState } from 'react';
import { Check } from 'lucide-react';
import { cn } from '@/lib/utils';

interface UploadSuccessAnimationProps {
    isUploading: boolean;
    onComplete?: () => void;
    className?: string;
}

export function UploadSuccessAnimation({
    isUploading,
    onComplete,
    className
}: UploadSuccessAnimationProps) {
    const [showSuccess, setShowSuccess] = useState(false);
    const [shouldRender, setShouldRender] = useState(false);

    useEffect(() => {
        if (isUploading) {
            setShouldRender(true);
            setShowSuccess(false);
        } else if (shouldRender && !isUploading) {
            // Upload completed, show success
            setShowSuccess(true);

            // Fade out after showing success
            const fadeTimer = setTimeout(() => {
                setShouldRender(false);
                onComplete?.();
            }, 1500);

            return () => clearTimeout(fadeTimer);
        }
    }, [isUploading, shouldRender, onComplete]);

    if (!shouldRender) return null;

    return (
        <div
            className={cn(
                "fixed top-4 right-4 z-50",
                showSuccess ? "animate-fade-out" : "animate-scale-in",
                className
            )}
        >
            <div className="relative w-16 h-16">
                {!showSuccess ? (
                    // Loading spinner
                    <div className="w-full h-full rounded-full border-4 border-muted">
                        <div className="absolute inset-0 rounded-full border-4 border-transparent border-t-primary animate-spin" />
                    </div>
                ) : (
                    // Success checkmark
                    <div className="w-full h-full rounded-full bg-green-500 flex items-center justify-center shadow-lg shadow-green-500/50">
                        <svg
                            className="w-10 h-10"
                            viewBox="0 0 24 24"
                            fill="none"
                            xmlns="http://www.w3.org/2000/svg"
                        >
                            <path
                                d="M5 13l4 4L19 7"
                                stroke="white"
                                strokeWidth="3"
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeDasharray="50"
                                strokeDashoffset="50"
                                className="animate-checkmark"
                            />
                        </svg>
                    </div>
                )}
            </div>
        </div>
    );
}
