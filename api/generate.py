from http.server import BaseHTTPRequestHandler
import json
import base64
from PIL import Image, ImageDraw, ImageFont
import io
import random

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            # Parse request
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            # Extract parameters
            content_type = data.get('type', 'hugot_tagalog')
            format_type = data.get('format', 'instagram_post')
            
            # Generate image
            image_base64 = self.generate_viral_image(content_type, format_type)
            
            # Return response
            response = {
                'success': True,
                'imageData': image_base64,
                'message': f'Generated {content_type} content successfully!'
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            # Error response
            error_response = {
                'success': False,
                'error': str(e)
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
    
    def generate_viral_image(self, content_type, format_type):
        """Generate viral image and return as base64"""
        
        # Content database
        content_db = {
            'hugot_tagalog': [
                "Yung tipong masaya ka sa kanya pero hindi ka niya priority.",
                "Bakit kaya mas madali magmahal kaysa makalimot?",
                "Hindi lahat ng forever, forever talaga.",
                "Yung feeling na ikaw lang ang may gusto sa relationship.",
                "Mas masakit yung hindi ka sinasagot kaysa sinasabi ng 'no'."
            ],
            'hugot_english': [
                "Sometimes the person you love the most is the one who hurts you the most.",
                "You can't force someone to love you back.",
                "Missing someone is your heart's way of reminding you that you love them.",
                "The hardest part of loving someone is accepting that they don't love you back.",
                "Sometimes you have to let go of the one you love to find happiness."
            ],
            'motivation': [
                "Your only limit is your mind.",
                "Success starts with self-discipline.",
                "Don't wait for opportunity. Create it.",
                "Winners focus on winning. Losers focus on winners.",
                "The best time to plant a tree was 20 years ago. The second best time is now."
            ]
        }
        
        # Select random content
        texts = content_db.get(content_type, content_db['hugot_tagalog'])
        selected_text = random.choice(texts)
        
        # Set dimensions based on format
        if format_type == 'instagram_post':
            width, height = 1080, 1080
        elif format_type == 'facebook_post':
            width, height = 1200, 630
        elif format_type == 'twitter_post':
            width, height = 1024, 512
        else:
            width, height = 1080, 1080
            
        # Create image
        image = Image.new('RGB', (width, height), color='#FF6B35')
        draw = ImageDraw.Draw(image)
        
        # FORCE massive font size - no more tiny text!
        font_size = 200  # FIXED 200px font regardless of image size
        print(f"DEBUG: FORCED font size: {font_size}px for {width}x{height} image")
        
        try:
            # Try multiple font paths
            font_paths = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/TTF/arial.ttf", 
                "/System/Library/Fonts/Arial.ttf",
                "/System/Library/Fonts/Helvetica.ttc"
            ]
            
            font = None
            for path in font_paths:
                try:
                    font = ImageFont.truetype(path, font_size)
                    print(f"DEBUG: Successfully loaded font: {path}")
                    break
                except:
                    continue
                    
            if font is None:
                raise Exception("No system fonts found")
                
        except Exception as e:
            print(f"DEBUG: All system fonts failed, using load_default (error: {e})")
            # Create a much larger default-style font
            try:
                font = ImageFont.load_default()
                font_size = 50  # Smaller but still visible with default font
                print(f"DEBUG: Using default font with size: {font_size}")
            except:
                # Last resort
                font = None
                font_size = 40
        
        # Add text with word wrapping
        words = selected_text.split()
        lines = []
        current_line = []
        
        # Handle text wrapping with massive font
        max_width = width - 100  # Generous margins
        
        if font:
            for word in words:
                test_line = ' '.join(current_line + [word])
                try:
                    text_width = draw.textbbox((0, 0), test_line, font=font)[2]
                    if text_width < max_width:
                        current_line.append(word)
                    else:
                        if current_line:
                            lines.append(' '.join(current_line))
                        current_line = [word]
                except:
                    # Fallback if textbbox fails
                    if len(test_line) * font_size * 0.6 < max_width:  # Rough estimate
                        current_line.append(word)
                    else:
                        if current_line:
                            lines.append(' '.join(current_line))
                        current_line = [word]
        else:
            # No font available, just split by word count
            for i, word in enumerate(words):
                if i % 3 == 0 and current_line:  # Every 3 words
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    current_line.append(word)
        
        if current_line:
            lines.append(' '.join(current_line))
        
        # Calculate text position with better spacing
        line_height = font_size + 20  # More line spacing for readability
        total_height = len(lines) * line_height
        start_y = (height - total_height) // 2
        
        # Draw text with better error handling
        for i, line in enumerate(lines):
            try:
                if font:
                    bbox = draw.textbbox((0, 0), line, font=font)
                    text_width = bbox[2] - bbox[0]
                else:
                    # Rough estimate if no font
                    text_width = len(line) * (font_size * 0.6)
                    
                x = (width - text_width) // 2
                y = start_y + i * line_height
                
                # Add text shadow for better visibility
                draw.text((x+3, y+3), line, font=font, fill='#000000')
                # Add main text in white
                draw.text((x, y), line, font=font, fill='#FFFFFF')
                print(f"DEBUG: Drew line {i}: '{line}' at position ({x}, {y})")
                
            except Exception as e:
                print(f"DEBUG: Error drawing line {i}: {e}")
                # Fallback drawing without advanced positioning
                simple_x = 50  
                simple_y = 50 + i * (font_size + 20)
                draw.text((simple_x, simple_y), line, fill='#FFFFFF')
                print(f"DEBUG: Used fallback drawing for line {i}")
        
        # Convert to base64
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        return f"data:image/png;base64,{image_base64}"