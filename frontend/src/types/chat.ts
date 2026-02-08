export interface SourceCitation {
  id: string;
  documentName: string;
  excerpt: string;
  confidence: number;
  confidenceLabel?: 'High' | 'Medium' | 'Low' | 'Null';
  pageNumber?: number;
  title?: string;
  isWeb?: boolean;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  sources?: SourceCitation[];
  images?: string[];
  feedback?: 'up' | 'down';
  isStopped?: boolean;
}

export interface ChatConversation {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: Date;
  updatedAt: Date;
  isPinned?: boolean;
}

export interface ChatSettings {
  temperature: number;
  model: string;
  maxTokens: number;
  systemPrompt: string;
}
