import { useState, useRef, useEffect, useLayoutEffect } from 'react';
import { Send, ImagePlus, X, Sparkles, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import { UploadSuccessAnimation } from './UploadSuccessAnimation';
import { ImagePreviewModal } from './ImagePreviewModal';
import { visionService } from '@/services/visionService';
import { cn } from '@/lib/utils';

interface ChatInputProps {
  onSend: (message: string, images?: string[]) => void;
  isLoading?: boolean;
  disabled?: boolean;
  value?: string;
  onChange?: (value: string) => void;
  placeholder?: string;
}

export function ChatInput({ onSend, isLoading, disabled, value, onChange, placeholder }: ChatInputProps) {
  const [internalMessage, setInternalMessage] = useState(value || '');
  const [images, setImages] = useState<string[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [previewImage, setPreviewImage] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [imageAnalysis, setImageAnalysis] = useState<Record<number, string>>({});
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const formRef = useRef<HTMLDivElement>(null);
  const { toast } = useToast();

  // Sync value from parent if provided (for editing/clearing)
  useEffect(() => {
    if (value !== undefined) {
      setInternalMessage(value);
    }
  }, [value]);

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newValue = e.target.value;
    setInternalMessage(newValue);
    onChange?.(newValue);
  };

  // Focus textarea when value changes externally
  useEffect(() => {
    if (value) {
      textareaRef.current?.focus();
    }
  }, [value]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if ((internalMessage.trim() || images.length > 0) && !isLoading && !disabled) {
      onSend(internalMessage.trim(), images.length > 0 ? images : undefined);
      setInternalMessage('');
      setImages([]);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  // Auto-resize textarea
  useLayoutEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto'; // Reset height to recalculate
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  }, [internalMessage]);

  // Process image file
  const processImageFile = (file: File) => {
    if (!file.type.startsWith('image/')) {
      toast({
        title: "Invalid file type",
        description: "Please upload an image file",
        variant: "destructive",
      });
      return;
    }

    const maxSizeMB = 10;
    const maxSizeBytes = maxSizeMB * 1024 * 1024;
    if (file.size > maxSizeBytes) {
      toast({
        title: "File too large",
        description: `Please upload an image smaller than ${maxSizeMB}MB`,
        variant: "destructive",
      });
      return;
    }


    // Show upload animation
    setIsUploading(true);

    const reader = new FileReader();
    reader.onloadstart = () => {
      setIsUploading(true);
    };
    reader.onload = (event) => {
      if (event.target?.result) {
        setImages((prev) => [...prev, event.target!.result as string]);
        // Upload complete, show success animation
        setTimeout(() => {
          setIsUploading(false);
        }, 100);
      }
    };
    reader.onerror = () => {
      setIsUploading(false);
      toast({
        title: "Upload failed",
        description: "Failed to read the image file",
        variant: "destructive",
      });
    };
    reader.readAsDataURL(file);

  };

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;

    Array.from(files).forEach((file) => {
      processImageFile(file);
    });

    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Handle paste from clipboard
  const handlePaste = (e: ClipboardEvent) => {
    const items = e.clipboardData?.items;
    if (!items) return;

    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      if (item.type.startsWith('image/')) {
        e.preventDefault();
        const file = item.getAsFile();
        if (file) {
          processImageFile(file);
          toast({
            description: "Image pasted from clipboard",
          });
        }
        break;
      }
    }
  };

  // Handle drag over
  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  // Handle drag leave
  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    // Only set dragging to false if we're leaving the form container
    if (e.currentTarget === formRef.current) {
      setIsDragging(false);
    }
  };

  // Handle drop
  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = e.dataTransfer.files;
    if (files) {
      Array.from(files).forEach((file) => {
        processImageFile(file);
      });
    }
  };

  const removeImage = (index: number) => {
    setImages((prev) => prev.filter((_, i) => i !== index));
    // Also remove analysis for this image
    setImageAnalysis((prev) => {
      const newAnalysis = { ...prev };
      delete newAnalysis[index];
      return newAnalysis;
    });
  };

  const handleAnalyzeImage = async (imageData: string, index: number) => {
    setIsAnalyzing(true);
    try {
      const result = await visionService.analyzeImage(imageData);
      setImageAnalysis((prev) => ({
        ...prev,
        [index]: result.analysis
      }));
      toast({
        title: "Analysis Complete",
        description: "Image analyzed successfully!",
      });
    } catch (error) {
      console.error('Vision analysis error:', error);
      toast({
        title: "Analysis Failed",
        description: error instanceof Error ? error.message : "Failed to analyze image",
        variant: "destructive",
      });
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Add paste event listener
  useEffect(() => {
    const handlePasteEvent = (e: ClipboardEvent) => handlePaste(e);
    document.addEventListener('paste', handlePasteEvent);

    return () => {
      document.removeEventListener('paste', handlePasteEvent);
    };
  }, []);

  return (
    <>
      {/* Upload Success Animation */}
      <UploadSuccessAnimation isUploading={isUploading} />

      {/* Image Preview Modal */}
      <ImagePreviewModal
        imageUrl={previewImage}
        onClose={() => setPreviewImage(null)}
      />

      <form onSubmit={handleSubmit} className="relative">
        <div
          ref={formRef}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={cn(
            "flex flex-col p-4 border-t border-border bg-gradient-to-t from-card to-transparent transition-all duration-200",
            isDragging && "bg-primary/5 border-primary/50"
          )}
        >
          {/* Drag overlay */}
          {isDragging && (
            <div className="absolute inset-0 bg-primary/10 border-2 border-dashed border-primary rounded-lg flex items-center justify-center z-10 pointer-events-none">
              <div className="text-center">
                <ImagePlus className="w-12 h-12 text-primary mx-auto mb-2" />
                <p className="text-sm font-medium text-primary">Drop images here</p>
              </div>
            </div>
          )}

          {/* Image Preview Section - Displays above text input */}
          {images.length > 0 && (
            <div className="flex flex-col gap-4 mb-4">
              {/* Image Container */}
              <div className="flex flex-wrap gap-3">
                {images.map((img, idx) => (
                  <div key={idx} className="flex flex-col gap-2">
                    <div className="relative group inline-block">
                      <img
                        src={img}
                        alt={`Upload ${idx + 1}`}
                        onClick={() => setPreviewImage(img)}
                        className={cn(
                          "w-32 h-32 object-cover rounded-xl border-2 border-border cursor-pointer hover:opacity-80 hover:border-primary/50 transition-all duration-200 shadow-lg",
                          imageAnalysis[idx] && "border-green-500/50"
                        )}
                      />
                      <button
                        type="button"
                        onClick={() => removeImage(idx)}
                        className="absolute -top-2 -right-2 w-6 h-6 bg-destructive text-destructive-foreground rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity shadow-md hover:scale-110 z-10"
                        aria-label="Remove image"
                      >
                        <X className="w-4 h-4" />
                      </button>

                      {/* Analyze Button */}
                      {!imageAnalysis[idx] && (
                        <button
                          type="button"
                          onClick={() => handleAnalyzeImage(img, idx)}
                          disabled={isAnalyzing}
                          className={cn(
                            "absolute bottom-2 right-2 p-1.5 rounded-full bg-background/80 backdrop-blur-sm border border-border shadow-sm transition-all opacity-0 group-hover:opacity-100 hover:bg-primary hover:text-primary-foreground",
                            isAnalyzing && "opacity-100"
                          )}
                          title="Analyze with Claude"
                        >
                          {isAnalyzing ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <Sparkles className="w-4 h-4" />
                          )}
                        </button>
                      )}
                    </div>

                    {/* Analysis Result Indicator */}
                    {imageAnalysis[idx] && (
                      <div className="max-w-[128px]">
                        <div className="text-[10px] uppercase font-bold text-green-600 mb-1 flex items-center gap-1">
                          <Sparkles className="w-3 h-3" /> Analyzed
                        </div>
                        <div className="text-xs text-muted-foreground line-clamp-3 bg-muted/50 p-1.5 rounded border border-border/50">
                          {imageAnalysis[idx]}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="relative flex items-end gap-3 bg-background rounded-2xl border border-input p-2 focus-within:ring-2 focus-within:ring-primary/30 focus-within:border-primary/50 transition-all duration-200">
            {/* Image Upload Button */}
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              multiple
              onChange={handleImageUpload}
              className="hidden"
            />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => fileInputRef.current?.click()}
              disabled={isLoading}
              className="h-10 w-10 shrink-0 text-muted-foreground hover:text-foreground hover:bg-muted rounded-xl transition-colors"
              title="Upload image (or paste/drag & drop)"
            >
              <ImagePlus className="w-5 h-5" />
            </Button>

            {/* Text Input */}
            <textarea
              ref={textareaRef}
              value={internalMessage}
              onChange={handleChange}
              onKeyDown={handleKeyDown}
              placeholder={placeholder || "Ask anything about IT support..."}
              disabled={disabled || isLoading}
              rows={1}
              className={cn(
                "flex-1 resize-none bg-transparent py-2.5 px-1",
                "text-sm text-foreground placeholder:text-muted-foreground",
                "focus:outline-none",
                "disabled:cursor-not-allowed disabled:opacity-50",
                "min-h-[40px] max-h-[200px]"
              )}
            />

            {/* Send Button */}
            <Button
              type="submit"
              size="icon"
              disabled={(!internalMessage.trim() && images.length === 0) || isLoading || disabled}
              className={cn(
                "h-10 w-10 shrink-0 rounded-xl transition-all duration-200",
                (internalMessage.trim() || images.length > 0) && !isLoading
                  ? "bg-primary hover:bg-primary/90 text-primary-foreground shadow-lg shadow-primary/25"
                  : "bg-muted text-muted-foreground hover:bg-muted"
              )}
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>

          {/* Keyboard hint */}
          <p className="text-xs text-muted-foreground text-center mt-3">
            IntelliQuery can make mistakes. Consider checking important information.
          </p>
        </div>
      </form>
    </>
  );
}
