export interface VisionAnalysisRequest {
    image_data: string;  // Base64 data URL
    prompt?: string;     // Optional question about the image
}

export interface VisionAnalysisResponse {
    analysis: string;
    model: string;
    tokens_used?: number;
}

export class VisionService {
    private baseUrl: string;
    private apiPrefix: string;

    constructor() {
        this.baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
        this.apiPrefix = '/api/v1';
    }

    async analyzeImage(imageData: string, prompt?: string): Promise<VisionAnalysisResponse> {
        const requestBody: VisionAnalysisRequest = {
            image_data: imageData,
            prompt: prompt
        };

        const response = await fetch(`${this.baseUrl}${this.apiPrefix}/vision/analyze`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody),
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Vision analysis failed' }));
            throw new Error(error.detail || `HTTP error! status: ${response.status}`);
        }

        return await response.json();
    }
}

export const visionService = new VisionService();
