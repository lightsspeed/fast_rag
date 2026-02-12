import io
import os
import fitz  # PyMuPDF
import cv2
import numpy as np
import pytesseract
from PIL import Image
from app.core.config import settings
from app.services.screenshot_analyzer import screenshot_analyzer
import logging
from groq import Groq

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

class ImageFilter:
    """Filters images to remove logos, lines, and non-meaningful content."""
    
    @staticmethod
    def should_keep_image(image_bytes: bytes, bbox: tuple, page_height: float) -> tuple[bool, str]:
        """
        Implements the logic from Step 1.3: Apply Filters.
        Returns (keep, reason).
        """
        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                return False, "invalid_image"

            height, width = img.shape[:2]
            y_position = bbox[1] # top coordinate

            # --- Filter 1: Size Filter ---
            if width < 100 or height < 100:
                return False, "too_small_logo"
            if width < 20 or height < 20:
                return False, "horizontal_line"
            if width > 2000 and height > 2000:
                return False, "full_page_background"

            # --- Filter 2: Aspect Ratio ---
            ratio = width / height
            if ratio > 10 or ratio < 0.1:
                return False, "decorative_line"

            # --- Filter 3: Color Variance & Unique Colors ---
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            color_variance = gray.std()
            if color_variance < 10:
                return False, "solid_color_patch"

            # Count unique colors (using subsampling for speed)
            # Resize image to speed up unique color counting
            small_img = cv2.resize(img, (50, 50), interpolation=cv2.INTER_AREA)
            unique_colors = len(np.unique(small_img.reshape(-1, small_img.shape[-1]), axis=0))
            if unique_colors < 5:
                return False, "simple_logo"

            # --- Filter 4: Position Filter ---
            # If in header or footer
            if y_position < 50 or y_position > (page_height - 50):
                if width < 300 or height < 300:
                    return False, "header_footer_logo"

            # --- Filter 5: Content Check (Mostly white) ---
            if np.mean(gray) > 250:
                return False, "blank_whitespace"

            return True, "meaningful_screenshot"
            
        except Exception as e:
            logger.error(f"Image filtering failed: {e}")
            return True, "error_fallback_keep" # Keep if filter fails

class ImageEnhancer:
    """Enhance images for better OCR/Vision performance (Refined for Step 2)."""
    
    @staticmethod
    def enhance_image(image_bytes: bytes, level: str = 'step2') -> bytes:
        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None: return image_bytes
            
            # 1. Grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            if level == 'step2':
                # --- Deskewing ---
                coords = np.column_stack(np.where(gray < 255))
                angle = cv2.minAreaRect(coords)[-1]
                # minAreaRect returns angle in range [-90, 0)
                if angle < -45:
                    angle = -(90 + angle)
                else:
                    angle = -angle
                
                if abs(angle) > 0.5: # Only rotate if significant
                    (h, w) = gray.shape[:2]
                    center = (w // 2, h // 2)
                    M = cv2.getRotationMatrix2D(center, angle, 1.0)
                    gray = cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

                # --- Denoise ---
                gray = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)

                # --- Contrast (CLAHE) ---
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
                gray = clahe.apply(gray)

                # --- Binarize (Otsu's) ---
                # Only binarize if we see low contrast or specifically for Tesseract
                _, gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            elif level == 'moderate':
                # Original moderate logic
                img = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
                gray = clahe.apply(gray)
                
            # Convert back to bytes
            is_success, buffer = cv2.imencode(".png", gray) # PNG better for OCR
            return buffer.tobytes() if is_success else image_bytes
            
        except Exception as e:
            logger.error(f"Enhancement failed: {e}")
            return image_bytes

class SmartPDFProcessor:
    """Main processor for PDFs with adaptive image handling (Tesseract -> PaddleOCR Fallback)."""
    
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.vision_model = settings.GROQ_VISION_MODEL
        self.paddle_ocr = None # Lazy load PaddleOCR
        logger.info(f"SmartPDFProcessor initialized. Primary: Tesseract, Fallback: PaddleOCR")

    def _get_paddle_ocr(self):
        """Lazy load PaddleOCR to save memory if not needed."""
        if self.paddle_ocr is None:
            try:
                from paddleocr import PaddleOCR
                # use_angle_cls=True enables orientation detection
                # lang='en' for English
                self.paddle_ocr = PaddleOCR(use_angle_cls=True, lang='en')
                logger.info("PaddleOCR engine initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize PaddleOCR: {e}")
        return self.paddle_ocr

    async def process_pdf(self, pdf_path: str) -> dict:
        """
        Process entire PDF. 
        Returns dict: {"full_text": str, "images_metadata": list[dict]}
        """
        full_text_parts = []
        images_metadata = []
        filename = os.path.basename(pdf_path)
        
        try:
            doc = fitz.open(pdf_path)
            
            for page_num, page in enumerate(doc):
                logger.info(f"Processing page {page_num + 1}")
                page_height = page.rect.height
                
                # 1. Extract Native Text
                text = page.get_text()
                if text.strip():
                    full_text_parts.append(text)
                
                # 2. Extract Images with position info
                image_info = page.get_image_info(xrefs=True)
                for img_index, img_meta in enumerate(image_info):
                    xref = img_meta['xref']
                    bbox = img_meta['bbox'] # (x0, y0, x1, y1)
                    
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    
                    # 3. Apply Smart Filters
                    keep, reason = ImageFilter.should_keep_image(image_bytes, bbox, page_height)
                    
                    if not keep:
                        logger.info(f"Image {img_index} on page {page_num+1} REJECTED: {reason}")
                        continue
                    
                    logger.info(f"Image {img_index} on page {page_num+1} PASSED filters: {reason}")
                    
                    # 4. Adaptive Pipeline: Tesseract -> PaddleOCR
                    # Get raw result with metrics
                    ocr_res = self._perform_ocr(image_bytes)
                    
                    if ocr_res["text"]:
                        # Append to full text for backward compatibility in chunking
                        full_text_parts.append(f"\n[Image {img_index+1}]\n{ocr_res['text']}\n")
                        
                        # 5. Build Rich Metadata (Step 3)
                        context = self._find_nearby_context(page, bbox)
                        analysis = screenshot_analyzer.analyze(ocr_res['text'])
                        
                        image_id = f"img_p{page_num+1}_{img_index+1}"
                        img_filename = f"{os.path.splitext(filename)[0]}_page{page_num+1}_img{img_index+1}.png"
                        
                        # Save Image to Disk for Frontend Display (Step 5)
                        static_dir = os.path.join(os.getcwd(), "app", "static", "images")
                        os.makedirs(static_dir, exist_ok=True)
                        save_path = os.path.join(static_dir, img_filename)
                        
                        with open(save_path, "wb") as f:
                            f.write(image_bytes)
                        
                        meta = {
                            "image_id": image_id,
                            "source_pdf": filename,
                            "page_number": page_num + 1,
                            "position": {"x": bbox[0], "y": bbox[1], "width": bbox[2]-bbox[0], "height": bbox[3]-bbox[1]},
                            "image_file": img_filename, # Filename only, served via /api/images/
                            "file_size_kb": round(len(image_bytes) / 1024, 1),
                            "ocr_result": {
                                "method": ocr_res["method"],
                                "text": ocr_res["text"],
                                "confidence": ocr_res["confidence"],
                                "language": "en",
                                "word_count": len(ocr_res["text"].split()),
                                "fallback_used": ocr_res["method"] == "paddleocr"
                            },
                            "content": analysis,
                            "context": context,
                            "searchable_content": f"{ocr_res['text']} {analysis['application']} {analysis['screenshot_type']} {' '.join(analysis['error_codes'])} {context['caption']} {context['section']}".lower(),
                            "quality": {
                                "ocr_confidence": ocr_res["confidence"],
                                "ocr_quality": "excellent" if ocr_res["confidence"] > 90 else "good" if ocr_res["confidence"] > 70 else "fair",
                                "needs_review": "[NEEDS_REVIEW]" in ocr_res["text"],
                                "both_ocr_failed": "[Extraction Failed]" in ocr_res["text"]
                            },
                            "display": {
                                "should_display": True,
                                "relevance_score": 1.0 if analysis["has_error"] else 0.8
                            }
                        }
                        images_metadata.append(meta)
                
            return {
                "full_text": "\n\n".join(full_text_parts),
                "images_metadata": images_metadata
            }
            
        except Exception as e:
            logger.error(f"PDF processing failed: {e}")
            raise e

    def _find_nearby_context(self, page, bbox):
        """Extracts contextual info (Step 3.4)."""
        try:
            page_rect = page.rect
            x0, y0, x1, y1 = bbox
            
            # Caption check below
            cap_rect = fitz.Rect(x0, y1, x1, min(y1 + 40, page_rect.height))
            caption = page.get_text("text", clip=cap_rect).strip()
            
            # Surrounding text window
            window_rect = fitz.Rect(0, max(0, y0 - 150), page_rect.width, min(y1 + 150, page_rect.height))
            surrounding = page.get_text("text", clip=window_rect).strip()
            
            # Simple section finding
            lines = surrounding.split('\n')
            section = lines[0][:100] if lines else ""
            
            return {
                "caption": caption if any(kw in caption.lower() for kw in ["figure", "screenshot", "img"]) else "",
                "section": section,
                "surrounding_text": surrounding[:500]
            }
        except Exception as e:
            return {"caption": "", "section": "", "surrounding_text": ""}

    def _perform_ocr(self, image_bytes: bytes) -> dict:
        """
        Performs Tesseract and PaddleOCR, handling fallbacks and quality gates.
        """
        from app.services.ocr_validator import ocr_validator
        from app.services.image_preprocessor import image_preprocessor
        
        # --- PHASE 2.1: Preprocessing for OCR Quality ---
        # Enhance image before OCR (15-25% accuracy boost)
        processed_bytes = image_preprocessor.enhance_for_ocr(image_bytes, image_type="auto")
        
        # Tesseract (Primary)
        tesseract_text = ""
        avg_confidence = 0
        try:
            img = Image.open(io.BytesIO(processed_bytes))  # Use enhanced image
            tess_config = '--oem 1 --psm 11'
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, config=tess_config)
            
            confidences = [int(c) for c in data['conf'] if c != -1]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            words = [w.strip() for w in data['text'] if w.strip()]
            tesseract_text = " ".join(words).strip()
            
            text_length = len(tesseract_text)
            gibberish_ratio = ocr_validator.calculate_gibberish_ratio(tesseract_text)
            
            # Decision
            should_fallback = False
            if avg_confidence < 70 or text_length < 20 or gibberish_ratio > 0.3:
                should_fallback = True
            
            if not should_fallback:
                return {"text": tesseract_text, "confidence": round(avg_confidence, 1), "method": "tesseract"}
                
        except Exception as e:
            logger.warning(f"Tesseract failed: {e}")

        # PaddleOCR (Fallback with Retry Strategy)
        try:
            from app.services.retry_strategy import OCRRetryStrategy
            
            paddle = self._get_paddle_ocr()
            nparr = np.frombuffer(processed_bytes, np.uint8)  # Use preprocessed image
            img_cv = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Call with circuit breaker and retry logic
            @OCRRetryStrategy.PADDLE_RETRY
            def paddle_ocr_with_retry():
                return OCRRetryStrategy.paddle_ocr_call_with_circuit_breaker(paddle, img_cv)
            
            paddle_result = paddle_ocr_with_retry()
            
            paddle_text = ""
            paddle_avg_conf = 0
            if paddle_result and paddle_result[0]:
                extracted_lines = []
                confidences = []
                for line in paddle_result[0]:
                    # PaddleOCR result format can vary by version
                    # Common formats: [[bbox, text], conf] or [[bbox], (text, conf)]
                    try:
                        if isinstance(line, (list, tuple)) and len(line) >= 2:
                            # Try format: [bbox, (text, confidence)]
                            if isinstance(line[1], (list, tuple)) and len(line[1]) == 2:
                                text, conf = line[1]
                                extracted_lines.append(str(text))
                                confidences.append(float(conf) * 100 if conf <= 1 else float(conf))
                            # Try format: [bbox, text, confidence]
                            elif len(line) >= 3:
                                text = line[1]
                                conf = line[2]
                                extracted_lines.append(str(text))
                                confidences.append(float(conf) * 100 if conf <= 1 else float(conf))
                    except Exception as parse_err:
                        logger.debug(f"Skipping line due to parsing error: {parse_err}")
                        continue
                
                paddle_text = " ".join(extracted_lines).strip()
                paddle_avg_conf = sum(confidences) / len(confidences) if confidences else 0
                
                # +10 Rule
                if paddle_avg_conf > (avg_confidence + 10):
                    return {"text": paddle_text, "confidence": round(paddle_avg_conf, 1), "method": "paddleocr"}
                
                if avg_confidence > (paddle_avg_conf + 10) and len(tesseract_text) >= 20:
                    return {"text": tesseract_text, "confidence": round(avg_confidence, 1), "method": "tesseract"}

                # Quality Gate
                if paddle_avg_conf >= 65 and len(paddle_text) >= 20:
                    return {"text": paddle_text, "confidence": round(paddle_avg_conf, 1), "method": "paddleocr"}
            
            # Both Failed Logic
            final_text = paddle_text if paddle_avg_conf > avg_confidence else tesseract_text
            res_text = f"[NEEDS_REVIEW] {final_text}" if final_text else "[Extraction Failed]"
            return {"text": res_text, "confidence": round(max(paddle_avg_conf, avg_confidence), 1), "method": "both_failed"}
                
        except Exception as e:
            logger.error(f"Fallback failed: {e}")
            return {"text": tesseract_text or "[Extraction Failed]", "confidence": avg_confidence, "method": "error"}

    async def _process_image_with_pipeline(self, image_bytes: bytes) -> str:
        """Wrapper for backward compatibility."""
        res = self._perform_ocr(image_bytes)
        return res["text"]

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
