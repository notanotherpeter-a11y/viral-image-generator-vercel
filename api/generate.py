from http.server import BaseHTTPRequestHandler
import json
import base64
from PIL import Image, ImageDraw, ImageFont
import io
import random
import os
import sys
from pathlib import Path
import logging
import traceback

# Configure logging for better debugging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            logger.info("=== NEW IMAGE GENERATION REQUEST ===")
            
            # Parse request
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            logger.info(f"Request data: {data}")
            
            # Extract parameters with better validation
            content_type = data.get('type', 'hugot_tagalog')
            format_type = data.get('format', 'instagram_post')
            custom_text = data.get('text', '')  # Support for custom text
            
            logger.info(f"Content type: {content_type}, Format: {format_type}")
            if custom_text:
                logger.info(f"Custom text provided: {custom_text[:50]}...")
            
            # Generate image
            image_base64 = self.generate_viral_image(content_type, format_type, custom_text)
            
            # Return response
            response = {
                'success': True,
                'imageData': image_base64,
                'message': f'Generated {content_type} content successfully!',
                'debug': {
                    'format': format_type,
                    'content_type': content_type,
                    'has_custom_text': bool(custom_text),
                    'python_version': sys.version,
                    'pil_version': getattr(Image, 'VERSION', 'unknown'),
                }
            }
            
            logger.info("✅ Image generated successfully!")
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            logger.error(f"❌ Error generating image: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Enhanced error response with debugging info
            error_response = {
                'success': False,
                'error': str(e),
                'debug': {
                    'error_type': type(e).__name__,
                    'python_version': sys.version,
                    'pil_version': getattr(Image, 'VERSION', 'unknown'),
                    'working_directory': os.getcwd(),
                    'font_directory_exists': os.path.exists('fonts'),
                    'traceback': traceback.format_exc()
                }
            }
            
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(error_response).encode())
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def get_optimal_font_size(self, width, height, text_length):
        """Calculate optimal font size based on image dimensions and text length"""
        # More conservative base font size calculation
        base_size = min(width, height) // 12  # Much more conservative: 1080px -> 90px base
        
        # Adjust for text length (shorter text = bigger font, but more moderate)
        if text_length < 20:
            multiplier = 1.4  # Reduced from 2.0
        elif text_length < 40:
            multiplier = 1.2  # Reduced from 1.6
        elif text_length < 80:
            multiplier = 1.0
        elif text_length < 120:
            multiplier = 0.8
        else:
            multiplier = 0.6
            
        optimal_size = int(base_size * multiplier)
        
        # More reasonable size limits
        min_size = width // 25  # Smaller minimum: 1080px -> 43px
        max_size = width // 8   # Smaller maximum: 1080px -> 135px
        
        final_size = max(min_size, min(optimal_size, max_size))
        
        logger.info(f"📏 Font size calculation: text_length={text_length}, base={base_size}, "
                   f"multiplier={multiplier}, optimal={optimal_size}, final={final_size}")
        
        return final_size
    
    def load_font(self, font_size):
        """Load font with comprehensive fallback system optimized for Vercel"""
        logger.info(f"🔤 Loading font with size: {font_size}")
        
        # Get current directory for font paths - optimized for Vercel structure
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        
        logger.info(f"Current directory: {current_dir}")
        logger.info(f"Project root: {project_root}")
        
        # Try bundled fonts first (these should work on Vercel)
        # Multiple possible paths to handle different deployment structures
        bundled_fonts = [
            # Relative to API directory
            os.path.join(project_root, "fonts", "OpenSans-Bold.ttf"),
            os.path.join(project_root, "fonts", "NotoSans-Bold.ttf"),
            # Relative paths from API
            os.path.join(current_dir, "..", "fonts", "OpenSans-Bold.ttf"),
            os.path.join(current_dir, "..", "fonts", "NotoSans-Bold.ttf"),
            # Direct relative paths
            "./fonts/OpenSans-Bold.ttf",
            "./fonts/NotoSans-Bold.ttf",
            "../fonts/OpenSans-Bold.ttf",
            "../fonts/NotoSans-Bold.ttf",
            # From working directory
            "fonts/OpenSans-Bold.ttf",
            "fonts/NotoSans-Bold.ttf",
        ]
        
        logger.info(f"Attempting to load bundled fonts...")
        
        for font_path in bundled_fonts:
            logger.info(f"Trying: {font_path}")
            try:
                if os.path.exists(font_path):
                    font = ImageFont.truetype(font_path, font_size)
                    logger.info(f"✅ Successfully loaded bundled font: {font_path}")
                    return font, font_size
                else:
                    logger.debug(f"❌ Font not found: {font_path}")
            except Exception as e:
                logger.warning(f"❌ Failed to load {font_path}: {e}")
                continue
        
        # Try system fonts as fallback (probably won't work on Vercel)
        system_fonts = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/TTF/arial.ttf", 
            "/System/Library/Fonts/Arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/Windows/Fonts/arial.ttf",
            "/Windows/Fonts/calibri.ttf"
        ]
        
        logger.info("Trying system fonts as fallback...")
        
        for font_path in system_fonts:
            try:
                if os.path.exists(font_path):
                    font = ImageFont.truetype(font_path, font_size)
                    logger.info(f"✅ Successfully loaded system font: {font_path}")
                    return font, font_size
            except Exception as e:
                logger.debug(f"❌ Failed to load {font_path}: {e}")
                continue
        
        # Final fallback: default font with better size handling
        logger.warning("⚠️ All font files failed, using default font with enhanced sizing")
        try:
            font = ImageFont.load_default()
            # Default font is much smaller, but we'll adjust our layout accordingly
            adjusted_size = font_size // 2  # Better ratio for default font
            logger.info(f"🔧 Using default font (effective size: {adjusted_size})")
            return font, adjusted_size
        except Exception as e:
            logger.error(f"❌ Even default font failed: {e}")
            return None, font_size
    
    def wrap_text(self, text, font, draw, max_width):
        """Intelligent text wrapping with font support"""
        words = text.split()
        lines = []
        current_line = []
        
        logger.info(f"📝 Wrapping text: '{text[:50]}...' with max_width: {max_width}")
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            
            try:
                if font and hasattr(draw, 'textbbox'):
                    # Use textbbox for accurate measurement
                    bbox = draw.textbbox((0, 0), test_line, font=font)
                    text_width = bbox[2] - bbox[0]
                else:
                    # Fallback: rough estimation
                    text_width = len(test_line) * 20  # Approximate
                    
                if text_width <= max_width:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                        current_line = [word]
                    else:
                        # Single word is too long, add it anyway
                        lines.append(word)
                        current_line = []
            except Exception as e:
                logger.warning(f"Error measuring text width: {e}")
                # Fallback to character-based wrapping
                if len(test_line) * 20 <= max_width:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                    current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        logger.info(f"Text wrapped into {len(lines)} lines")
        return lines
    
    def generate_viral_image(self, content_type, format_type, custom_text=''):
        """Generate viral image with improved font handling and debugging"""
        
        logger.info(f"🚀 Generating viral image - Type: {content_type}, Format: {format_type}")
        
        # Enhanced content database with more viral content
        content_db = {
            'hugot_tagalog': [
                "Yung tipong masaya ka sa kanya pero hindi ka niya priority.",
                "Bakit kaya mas madali magmahal kaysa makalimot?",
                "Hindi lahat ng forever, forever talaga.",
                "Yung feeling na ikaw lang ang may gusto sa relationship.",
                "Mas masakit yung hindi ka sinasagot kaysa sinasabi ng 'no'.",
                "Sana pwedeng i-block din yung feelings gaya ng social media.",
                "Yung nagmahal ng totoo pero naging joke time lang pala.",
                "Minsan mas okay pa yung single kaysa sa inlove ka lang mag-isa.",
                "Yung akala mo forever kayo, pero ikaw lang pala nag-isip nun.",
                "Mahirap magpanggap na okay ka lang kapag nasasaktan ka na."
            ],
            'hugot_english': [
                "Sometimes the person you love the most is the one who hurts you the most.",
                "You can't force someone to love you back.",
                "Missing someone is your heart's way of reminding you that you love them.",
                "The hardest part of loving someone is accepting that they don't love you back.",
                "Sometimes you have to let go of the one you love to find happiness.",
                "Love is not about possession, it's about appreciation.",
                "The worst feeling is when someone makes you feel special, then suddenly leaves you hanging.",
                "Don't chase people. Be yourself, do your own thing and work hard.",
                "You deserve someone who chooses you every single day.",
                "The right person will love all the things about you that the wrong person was intimidated by."
            ],
            'motivation': [
                "Your only limit is your mind.",
                "Success starts with self-discipline.",
                "Don't wait for opportunity. Create it.",
                "Winners focus on winning. Losers focus on winners.",
                "The best time to plant a tree was 20 years ago. The second best time is now.",
                "You are never too old to set another goal or to dream a new dream.",
                "Success is not final, failure is not fatal: it is the courage to continue that counts.",
                "Believe you can and you're halfway there.",
                "The only way to do great work is to love what you do.",
                "Don't be pushed around by fears. Be led by your dreams."
            ],
            'custom': [custom_text] if custom_text.strip() else ["Custom text not provided"]
        }
        
        # Select text content
        texts = content_db.get(content_type, content_db['hugot_tagalog'])
        selected_text = random.choice(texts) if texts else "No content available"
        
        logger.info(f"Selected text: '{selected_text}'")
        
        # Set dimensions based on format
        format_dimensions = {
            'instagram_post': (1080, 1080),
            'facebook_post': (1200, 630),
            'twitter_post': (1024, 512)
        }
        
        width, height = format_dimensions.get(format_type, (1080, 1080))
        logger.info(f"Image dimensions: {width}x{height}")
        
        # Create solid black background for maximum contrast
        image = Image.new('RGB', (width, height), color=(0, 0, 0))  # Pure black background
        
        draw = ImageDraw.Draw(image)
        
        # Calculate optimal font size
        font_size = self.get_optimal_font_size(width, height, len(selected_text))
        
        # Load font
        font, actual_font_size = self.load_font(font_size)
        
        # Prepare text wrapping with more generous margins for readability
        margin = 80  # Larger margin for better visual appeal
        max_text_width = width - (margin * 2)
        lines = self.wrap_text(selected_text, font, draw, max_text_width)
        
        # Calculate text positioning
        line_height = actual_font_size + 30  # More spacing for better readability
        total_text_height = len(lines) * line_height
        start_y = (height - total_text_height) // 2
        
        logger.info(f"📐 Text layout: {len(lines)} lines, line_height={line_height}, start_y={start_y}")
        
        # Draw text with enhanced shadow for better readability
        for i, line in enumerate(lines):
            try:
                # Calculate text position for centering
                if font and hasattr(draw, 'textbbox'):
                    bbox = draw.textbbox((0, 0), line, font=font)
                    text_width = bbox[2] - bbox[0]
                else:
                    text_width = len(line) * (actual_font_size * 0.6)
                    
                x = max(margin, (width - text_width) // 2)  # Center with minimum margin
                y = start_y + i * line_height
                
                # Add subtle glow effect for better readability on black
                glow_intensity = 3
                # Draw white glow layers behind text
                for glow in range(glow_intensity, 0, -1):
                    glow_alpha = 60 // glow  # Stronger glow closer to text
                    for dx in range(-glow, glow + 1):
                        for dy in range(-glow, glow + 1):
                            if dx != 0 or dy != 0:  # Skip center
                                draw.text((x + dx, y + dy), line, font=font, fill=(255, 255, 255, glow_alpha))
                
                # Draw main text in soft white for easier reading
                # Using off-white (245, 245, 245) instead of pure white (255, 255, 255)
                draw.text((x, y), line, font=font, fill=(245, 245, 245))
                
                logger.info(f"Drew line {i+1}: '{line[:30]}...' at ({x}, {y})")
                
            except Exception as e:
                logger.error(f"Error drawing line {i}: {e}")
                # Emergency fallback positioning
                simple_x = margin
                simple_y = 100 + i * (actual_font_size + 20)
                draw.text((simple_x, simple_y), line, font=font, fill=(255, 255, 255))
                logger.info(f"Used fallback positioning for line {i}")
        
        # Add subtle branding
        try:
            brand_font_size = max(16, width // 80)
            if font:
                brand_font = ImageFont.truetype(font.path if hasattr(font, 'path') else None, brand_font_size)
            else:
                brand_font = None
            
            brand_text = "viralstudio.ai ✨"
            brand_x = width - 200
            brand_y = height - 30
            
            # Draw subtle brand text - more visible on black background
            draw.text((brand_x, brand_y), brand_text, font=brand_font, fill=(180, 180, 180, 180))
        except Exception as e:
            logger.debug(f"Could not add branding: {e}")
        
        # Convert to base64 with optimization
        buffer = io.BytesIO()
        image.save(buffer, format='PNG', optimize=True, compress_level=6)
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        logger.info(f"✅ Image generated successfully! Size: {len(image_base64)} base64 characters")
        
        return f"data:image/png;base64,{image_base64}"