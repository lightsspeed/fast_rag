import io
import fitz  # PyMuPDF
import cv2
import numpy as np
import pytesseract
from PIL import Image
from groq import Groq
from app.core.config import settings
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Tesseract path for Windows if needed
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class ImageQualityAssessor:
    """Assess image quality to determine processing strategy."""
    
    @staticmethod
    def assess_image(image_bytes: bytes) -> dict:
        try:
            # Convert to cv2 image
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                return {'quality': 'invalid', 'score': 0}

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            height, width = gray.shape
            
            # 1. Sharpness (Laplacian variance)
            sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            # 2. Contrast
            contrast = gray.std()
            
            # 3. Resolution Score
            resolution_score = min(100, (width * height) / 10000)
            
            # 4. Text Density (Simple edges estimation)
            edges = cv2.Canny(gray, 100, 200)
            text_density = (np.count_nonzero(edges) / (width * height)) * 100
            
            # Normalized Score (0-100)
            # Sharpness is usually 0-1000+, but >500 is good. Cap at 500 for calc.
            norm_sharpness = min(sharpness, 500) / 5
            norm_contrast = min(contrast, 127) / 1.27
            
            score = (norm_sharpness * 0.4) + (norm_contrast * 0.3) + (resolution_score * 0.3)
            
            # Classification
            quality = 'high'
            if score < 30: quality = 'very_low'
            elif score < 50: quality = 'low'
            elif score < 70: quality = 'medium'
            
            return {
                'quality': quality,
                'score': round(score, 1),
                'sharpness': round(sharpness, 1),
                'resolution': {'width': width, 'height': height},
                'text_density': round(text_density, 1),
                'method': ImageQualityAssessor._recommend_method(quality, text_density)
            }
        except Exception as e:
            logger.error(f"Image assessment failed: {e}")
            return {'quality': 'error', 'score': 0, 'method': 'tesseract_high'}

    @staticmethod
    def _recommend_method(quality: str, density: float) -> str:
        if quality == 'high':
            return 'tesseract_high' if density > 5 else 'vision' # Low density might be diagram
        elif quality == 'medium':
            return 'tesseract_enhanced' if density > 10 else 'vision'
        elif quality == 'low':
            return 'vision_then_ocr'
        else:
            return 'vision_then_ocr'

class ImageEnhancer:
    """Enhance images for better OCR/Vision performance."""
    
    @staticmethod
    def enhance_image(image_bytes: bytes, level: str = 'moderate') -> bytes:
        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None: return image_bytes
            
            # Basic enhancement for all
            # Denoise
            img = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)
            
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            if level == 'aggressive':
                # Upscale
                gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
                # Thresholding
                gray = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                           cv2.THRESH_BINARY, 11, 2)
            elif level == 'moderate':
                # Contrast stretching (CLAHE)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
                gray = clahe.apply(gray)
                
            # Convert back to bytes
            is_success, buffer = cv2.imencode(".jpg", gray)
            return buffer.tobytes() if is_success else image_bytes
            
        except Exception as e:
            logger.error(f"Enhancement failed: {e}")
            return image_bytes

class SmartPDFProcessor:
    """Main processor for PDFs with adaptive image handling."""
    
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.vision_model = settings.GROQ_VISION_MODEL
        logger.info(f"SmartPDFProcessor initialized with vision_model: {self.vision_model}")

    async def process_pdf(self, pdf_path: str) -> str:
        """Process entire PDF and return combined text content."""
        full_content = []
        
        try:
            doc = fitz.open(pdf_path)
            
            for page_num, page in enumerate(doc):
                logger.info(f"Processing page {page_num + 1}")
                page_content = []
                
                # 1. Extract Native Text
                text = page.get_text()
                if text.strip():
                    page_content.append(f"--- Page {page_num + 1} Text ---\n{text}")
                
                # 2. Extract Images
                image_list = page.get_images()
                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    
                    # 3. Assess Quality
                    quality_info = ImageQualityAssessor.assess_image(image_bytes)
                    logger.info(f"Image {img_index}: Quality={quality_info['quality']} ({quality_info['score']}), Method={quality_info['method']}")
                    
                    # 4. Adaptive Processing
                    processed_text = await self._process_image_adaptively(image_bytes, quality_info)
                    
                    if processed_text:
                        page_content.append(f"\n[Image {img_index+1} Description]\n{processed_text}\n")
                
                full_content.append("\n".join(page_content))
                
            return "\n\n".join(full_content)
            
        except Exception as e:
            logger.error(f"PDF processing failed: {e}")
            raise e

    async def _process_image_adaptively(self, image_bytes: bytes, quality_info: dict) -> str:
        method = quality_info['method']
        
        try:
            if 'tesseract' in method:
                # Try OCR
                try:
                    # Check if enhanced is needed
                    if 'enhanced' in method:
                        image_bytes = ImageEnhancer.enhance_image(image_bytes, 'moderate')
                    
                    img = Image.open(io.BytesIO(image_bytes))
                    text = pytesseract.image_to_string(img)
                    
                    if len(text.strip()) > 50:
                        return text
                    
                    # Fallback if OCR returned too little
                    logger.info("OCR result poor, falling back to Vision")
                    return await self._call_vision_model(image_bytes)
                    
                except Exception as e:
                    logger.warning(f"OCR missing or failed: {e}. Falling back to Vision.")
                    return await self._call_vision_model(image_bytes)
            
            else:
                # Vision Model
                if method == 'vision_enhanced':
                    image_bytes = ImageEnhancer.enhance_image(image_bytes, 'moderate')
                
                return await self._call_vision_model(image_bytes)
                
        except Exception as e:
            logger.error(f"Image processing error: {e}")
            return "[Error extracting image content]"

    async def _call_vision_model(self, image_bytes: bytes) -> str:
        """Call Groq Vision API."""
        if not self.vision_model:
            return "[Vision Model Not Configured - Content Skipped]"

        import base64
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        
        prompt = """Extract and describe ALL content from this image:
1. If TEXT: Extract every visible word accurately maintaining structure.
2. If TABLES: Convert to markdown table format.
3. If CHARTS: Extract all data points, describe trends and axis.
4. If DIAGRAMS: Explain structure and connections.
Be extremely detailed."""

        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                },
                            },
                        ],
                    }
                ],
                model=self.vision_model,
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            logger.error(f"Groq Vision API failed: {e}")
            return ""

smart_pdf_processor = SmartPDFProcessor()
