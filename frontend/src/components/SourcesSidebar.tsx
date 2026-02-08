import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { ScrollArea } from "@/components/ui/scroll-area";
import { SourceCard } from "./SourceCard";
import type { SourceCitation } from "@/types/chat";
import { Library } from "lucide-react";

interface SourcesSidebarProps {
  isOpen: boolean;
  onClose: () => void;
  sources: SourceCitation[];
}

export function SourcesSidebar({ isOpen, onClose, sources }: SourcesSidebarProps) {
  // Filter out low confidence sources and sort by confidence descending
  // Dynamic filtering: Show only "High" and "Medium" sources if available.
  // fallback to showing the top 2 "Low" sources if no better ones exist.
  const allValidSources = sources.filter(s => s.confidence > 0.15)
    .sort((a, b) => b.confidence - a.confidence);

  const highQualitySources = allValidSources.filter(s => s.confidence >= 0.4);

  const sortedSources = highQualitySources.length > 0
    ? highQualitySources
    : allValidSources.slice(0, 2);

  return (
    <Sheet open={isOpen} onOpenChange={onClose}>
      <SheetContent side="right" className="w-[400px] sm:w-[540px] p-0 flex flex-col">
        <SheetHeader className="p-6 border-b">
          <div className="flex items-center gap-2">
            <Library className="w-5 h-5 text-primary" />
            <SheetTitle>Sources</SheetTitle>
          </div>
          <SheetDescription>
            Documents used to generate this answer, ranked by confidence score.
          </SheetDescription>
        </SheetHeader>

        <ScrollArea className="flex-1 p-6">
          <div className="space-y-4">
            {sortedSources.length > 0 ? (
              sortedSources.map((source, index) => (
                <SourceCard
                  key={source.id || index}
                  source={source}
                  index={index}
                />
              ))
            ) : (
              <div className="text-center py-10">
                <p className="text-muted-foreground">No sources available for this message.</p>
              </div>
            )}
          </div>
        </ScrollArea>
      </SheetContent>
    </Sheet>
  );
}
