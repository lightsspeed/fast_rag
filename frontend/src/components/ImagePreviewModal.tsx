import { useEffect } from 'react';
import { X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface ImagePreviewModalProps {
    imageUrl: string | null;
    onClose: () => void;
}

export function ImagePreviewModal({ imageUrl, onClose }: ImagePreviewModalProps) {
    // Close on ESC key
    useEffect(() => {
        const handleEscape = (e: KeyboardEvent) => {
            if (e.key === 'Escape') {
                onClose();
            }
        };

        if (imageUrl) {
            document.addEventListener('keydown', handleEscape);
            // Prevent body scroll
            document.body.style.overflow = 'hidden';
        }

        return () => {
            document.removeEventListener('keydown', handleEscape);
            // Restore body scroll
            document.body.style.overflow = 'unset';
        };
    }, [imageUrl, onClose]);

    if (!imageUrl) return null;

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center animate-fade-in"
            onClick={onClose}
        >
            {/* Backdrop */}
            <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" />

            {/* Modal Content */}
            <div
                className="relative z-10 max-w-[90vw] max-h-[90vh] animate-zoom-in"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Close Button */}
                <Button
                    variant="ghost"
                    size="icon"
                    onClick={onClose}
                    className="absolute -top-12 right-0 h-10 w-10 text-white hover:text-white hover:bg-white/20 rounded-full"
                >
                    <X className="h-6 w-6" />
                </Button>

                {/* Image */}
                <img
                    src={imageUrl}
                    alt="Preview"
                    className="max-w-full max-h-[90vh] object-contain rounded-lg shadow-2xl"
                />
            </div>
        </div>
    );
}
