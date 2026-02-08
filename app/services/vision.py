import base64
import re
from typing import Optional, Tuple, List, AsyncGenerator
from groq import Groq
import google.generativeai as genai
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class VisionService:
    def __init__(self):
        self.groq_client = Groq(api_key=settings.GROQ_API_KEY)
        self.groq_model = settings.GROQ_VISION_MODEL
        
        # Initialize Google client
        self.gemini_configured = False
        if settings.GOOGLE_API_KEY:
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            self.gemini_model_name = settings.GEMINI_MODEL
            self.gemini_configured = True
        else:
            logger.info("GOOGLE_API_KEY not set. Gemini vision analysis not available.")

    def parse_base64_data_url(self, data_url: str) -> Tuple[str, str]:
        """Parse a base64 data URL and extract media type and base64 data."""
        pattern = r'^data:([^;]+);base64,(.+)$'
        match = re.match(pattern, data_url)
        if not match:
            raise ValueError("Invalid base64 data URL format. Expected 'data:<media_type>;base64,<data>'")
        return match.group(1), match.group(2)

    async def analyze_image(self, image_data: str, prompt: Optional[str] = None) -> dict:
        """
        Analyze image using Gemini.
        """
        if self.gemini_configured:
            return await self.analyze_image_with_gemini(image_data, prompt)
        else:
            raise ValueError("Google API key not configured. Please set GOOGLE_API_KEY.")

    async def analyze_image_with_gemini(self, image_data: str, prompt: Optional[str] = None) -> dict:
        """Analyze image using Google Gemini."""
        if not self.gemini_configured:
            raise ValueError("Google API key not configured.")

        try:
            media_type, base64_data = self.parse_base64_data_url(image_data)
            
            # Default prompt
            if not prompt:
                prompt = "Describe this image in detail. Focus on any error messages or text visible."
            
            logger.info(f"Starting Gemini analysis with prompt: '{prompt}'")

            # Decode base64 to bytes for Gemini
            image_bytes = base64.b64decode(base64_data)
            
            # Create content for Gemini
            # Gemini expects a list of parts: [prompt, image_blob]
            model = genai.GenerativeModel(self.gemini_model_name)
            
            response = model.generate_content([
                prompt,
                {
                    "mime_type": media_type,
                    "data": image_bytes
                }
            ])
            
            analysis = response.text
            if not analysis:
                logger.warning("Gemini returned empty text for image analysis.")
                analysis = "No description available for this image."
            
            logger.info(f"Gemini analysis successful. Length: {len(analysis)} characters.")
            
            # Gemini usage metadata might not be directly available in the same way, using dummy token count or estimate
            tokens_used = 0 # response.usage_metadata is available in newer versions
            
            logger.info(f"Gemini vision analysis completed for {media_type}")
            
            return {
                "analysis": analysis,
                "model": self.gemini_model_name,
                "tokens_used": tokens_used
            }
            
        except Exception as e:
            logger.error(f"Gemini vision analysis failed: {e}")
            raise Exception(f"Gemini analysis failed: {str(e)}")



    async def describe_image(self, image_path: str) -> str:
        """Convert image to base64 and get a technical description from Groq."""
        try:
            with open(image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')

            completion = self.groq_client.chat.completions.create(
                model=self.groq_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Describe this technical diagram or image from a document in detail for a searchable database. Focus on names of components, flow of data, and specific text visible."},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{encoded_string}",
                                },
                            },
                        ],
                    }
                ],
                temperature=0.1,
                max_tokens=1024,
            )
            return completion.choices[0].message.content
        except Exception as e:
            logger.error(f"Groq vision analysis failed: {e}")
            return f"Image extraction failed: {str(e)}"

    async def generate_multimodal_stream(
        self, 
        query: str, 
        image_data_list: List[str], 
        context_chunks: List[dict]
    ) -> AsyncGenerator[str, None]:
        """
        Generate a multimodal response using Gemini 2.0 Flash, 
        incorporating user query, multiple images, and RAG context chunks.
        """
        if not self.gemini_configured:
            raise ValueError("Google API key not configured.")

        try:
            model = genai.GenerativeModel(self.gemini_model_name)
            
            # Prepare context text
            context_text = "\n\n".join(
                [f"[Chunk {i+1}]\n{chunk['text']}" for i, chunk in enumerate(context_chunks)]
            )
            
            # Prepare prompt
            # We combine system instructions, query and context into a single large prompt prefix
            prompt_prefix = f"""You are a highly capable AI specialized in technical troubleshooting and document analysis. Your goal is to provide a comprehensive, in-depth explanation based on the provided context chunks and images.

**Instructions for Integration:**
1. **Analyze Vision First**: If an image (like an error message or diagram) is present, identify its core components first.
2. **Comprehensive Reasoning**: Do not just give a brief summary. Provide a detailed, step-by-step technical explanation that connects what you see in the image with the information found in the document context.
3. **NO INLINE CITATIONS**: Do not use citations like "[Chunk 1]" or "[1]" in your response text. Provide a natural, professionally written technical answer. 
4. **Context Filtering**: If the provided documents are unrelated to the image, focus on analyzing the image and state that the specific documents provided do not contain additional details for this exact situation.
5. **Formatting**: Use clear markdown headers, bullet points, and code blocks as needed to make the technical information easily readable.

**Context from Documents:**
{context_text}

**User Question**: {query}
"""
            
            # Prepare parts list for Gemini
            prompt_parts = [prompt_prefix]
            
            # Add images
            for img_data in image_data_list:
                try:
                    media_type, base64_data = self.parse_base64_data_url(img_data)
                    image_bytes = base64.b64decode(base64_data)
                    prompt_parts.append({
                        "mime_type": media_type,
                        "data": image_bytes
                    })
                except Exception as e:
                    logger.warning(f"Failed to process image for multimodal stream: {e}")
            
            # Use generate_content_async for streaming
            # Note: in some versions it's generate_content(..., stream=True) and you iterate
            # in newer genai it's async
            response = await model.generate_content_async(prompt_parts, stream=True)
            
            async for chunk in response:
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            logger.error(f"Multimodal generation failed: {e}")
            yield f"Error generating multimodal response: {str(e)}"

    async def get_visual_keywords(self, image_data: str) -> str:
        """
        Quickly extract 3-5 technical keywords from an image to improve RAG retrieval.
        Returns a comma-separated string of keywords.
        """
        if not self.gemini_configured:
            return ""

        try:
            model = genai.GenerativeModel(self.gemini_model_name)
            media_type, base64_data = self.parse_base64_data_url(image_data)
            image_bytes = base64.b64decode(base64_data)
            
            prompt = "Extract 3-5 specific technical keywords or subject names from this image to help me search for related technical documentation. Return ONLY the keywords separated by commas, nothing else."
            
            response = await model.generate_content_async([
                prompt,
                {
                    "mime_type": media_type,
                    "data": image_bytes
                }
            ])
            
            keywords = response.text.strip()
            # Basic sanitization
            keywords = re.sub(r'[^a-zA-Z0-9,\s]', '', keywords)
            logger.info(f"Visual keywords extracted: {keywords}")
            return keywords
        except Exception as e:
            logger.error(f"Visual keyword extraction failed: {e}")
            return ""

vision_service = VisionService()
