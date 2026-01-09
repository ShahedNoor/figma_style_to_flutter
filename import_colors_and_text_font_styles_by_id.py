import requests
import re
import os
import sys

# ===== CONFIGURATION =====
FIGMA_TOKEN = "figma_token"
FILE_KEY = "file_key"
NODE_ID = "node_id"  # The ID of the specific node/frame to process

COLORS_OUTPUT = 'colors.xml'
TEXTSTYLES_OUTPUT = 'text_font_style.dart'

# Fallback fonts configuration
FALLBACK_FONTS = [
    'Open Sans',
    'Roboto',
    'Noto Sans',
]

headers = {
    "X-Figma-Token": FIGMA_TOKEN
}

# ===== HELPER FUNCTIONS =====

def rgb_to_hex(r, g, b):
    """Convert Figma RGB (0-1 range) to hex string."""
    return "{:02X}{:02X}{:02X}".format(round(r*255), round(g*255), round(b*255))

def rgba_to_hex(rgba):
    """Convert Figma RGBA to hex without #."""
    r = round(rgba['r'] * 255)
    g = round(rgba['g'] * 255)
    b = round(rgba['b'] * 255)
    return f"{r:02X}{g:02X}{b:02X}"

def parse_text_style(node):
    """Parse text style properties from a Figma text node."""
    try:
        style = node['style']
        fontFamily = style.get('fontFamily', None)
        
        # If font family not found, use placeholder
        if not fontFamily:
            fontFamily = "FontNotFound"
            print(f"⚠️  Warning: Font family not found in node, using 'FontNotFound' as placeholder")
        
        fontWeight = style.get('fontWeight', 400)
        fontSize = int(style.get('fontSize', 14))
        
        fills = node.get('fills', [])
        color = "000000"
        if fills:
            solid_fill = next((f for f in fills if f['type']=="SOLID"), None)
            if solid_fill:
                color = rgba_to_hex(solid_fill['color'])
        
        return fontFamily, fontWeight, fontSize, color
    except Exception as e:
        print(f"⚠️  Warning: Error parsing text style - {str(e)}, using fallback values")
        return "FontNotFound", 400, 14, "000000"

# ===== MAIN PROCESSING =====

def process_figma_file():
    """Fetch Figma node and process colors and text styles."""
    print(f"Fetching Figma node {NODE_ID} from file {FILE_KEY}...")
    url = f"https://api.figma.com/v1/files/{FILE_KEY}/nodes?ids={NODE_ID}"
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Failed to fetch Figma file: {response.text}")
        return
    
    figma_data = response.json()
    print("✅ Figma data fetched successfully")
    
    # Process colors and text styles
    colors = {}  # Use dict to store unique colors with names
    text_styles = []
    unique_styles = set()
    
    def parse_node(node):
        # Extract colors from fills
        if "fills" in node:
            for fill in node["fills"]:
                if fill["type"] == "SOLID":
                    color = fill["color"]
                    hex_code = rgb_to_hex(color["r"], color["g"], color["b"])
                    color_name = f"c{hex_code}"
                    color_value = f"#{hex_code}"
                    colors[color_name] = color_value
        
        # Extract text styles
        if node.get('type') == "TEXT":
            fontFamily, fontWeight, fontSize, color = parse_text_style(node)
            fontName = re.sub(r'\W+', '', fontFamily)
            
            # Create style name
            style_name = f"textStyle{fontSize}c{color}{fontName}{fontWeight}"
            
            # Create style definition
            style_def = {
                'name': style_name,
                'fontFamily': fontFamily,
                'color': color,
                'fontSize': fontSize,
                'fontWeight': fontWeight
            }
            
            # Check for uniqueness
            style_key = f"{fontSize}_{color}_{fontWeight}_{fontName}"
            if style_key not in unique_styles:
                unique_styles.add(style_key)
                text_styles.append(style_def)
        
        # Recursively parse children
        if "children" in node:
            for child in node["children"]:
                parse_node(child)
    
    # Extract the specific node data
    nodes_map = figma_data.get("nodes", {})
    # Note: Figma API can be tricky with exact ID formatting in keys (e.g. escaping), 
    # but usually it matches the requested ID.
    target_node_data = nodes_map.get(NODE_ID)
    
    if not target_node_data:
        # Fallback: try to find the node if the key is slightly different or just take the first one
        if len(nodes_map) == 1:
            target_node_data = list(nodes_map.values())[0]
            print(f"⚠️  Note: Used the single available node in response, key was: {list(nodes_map.keys())[0]}")
        else:
            print(f"❌ Node {NODE_ID} not found in response keys: {list(nodes_map.keys())}")
            return

    root_node = target_node_data.get("document")
    if not root_node:
         print(f"❌ Document structure not found for node {NODE_ID}.")
         return
         
    # Start parsing from the target node
    parse_node(root_node)
    
    # Save colors
    save_colors_xml(colors)
    
    # Save text styles
    save_text_styles_dart(text_styles)

def save_colors_xml(colors):
    """Create complete colors.xml file."""
    print(f"\nGenerating {COLORS_OUTPUT}...")
    
    # Sort colors by name for better organization
    sorted_colors = sorted(colors.items())
    
    xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n<colors>\n'
    
    for color_name, color_value in sorted_colors:
        xml_content += f'  <color name="{color_name}">{color_value}</color>\n'
    
    xml_content += '</colors>\n'
    
    # Write to file
    with open(COLORS_OUTPUT, 'w', encoding='utf-8') as f:
        f.write(xml_content)
    
    print(f"✅ Generated {COLORS_OUTPUT} with {len(colors)} colors")

def save_text_styles_dart(text_styles):
    """Create complete text_font_style.dart file with proper Flutter structure."""
    print(f"\nGenerating {TEXTSTYLES_OUTPUT}...")
    
    # Sort styles by fontSize, then color for better organization
    sorted_styles = sorted(text_styles, key=lambda x: (x['fontSize'], x['color'], x['fontWeight']))
    
    dart_content = '''import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:your_app_name/gen/colors.gen.dart';

class TextFontStyle {
  TextFontStyle._();

  // Fallback Fonts
  static const fallbackFonts = [
'''
    
    # Generate fallback fonts list
    for font in FALLBACK_FONTS:
        dart_content += f"    '{font}',\n"
        
    dart_content += '''  ];

'''

    
    for style in sorted_styles:
        font_family = style['fontFamily']
        color_name = f"c{style['color']}"
        
        dart_content += f'''  static final {style['name']} = TextStyle(
    fontFamily: "{font_family}",
    fontFamilyFallback: fallbackFonts,
    color: AppColors.{color_name},
    fontSize: {style['fontSize']}.sp,
    fontWeight: FontWeight.w{style['fontWeight']},
  );

'''
    
    dart_content += '}\n'
    
    # Write to file
    with open(TEXTSTYLES_OUTPUT, 'w', encoding='utf-8') as f:
        f.write(dart_content)
    
    print(f"✅ Generated {TEXTSTYLES_OUTPUT} with {len(text_styles)} text styles")

# ===== RUN =====

if __name__ == "__main__":
    print("=" * 60)
    print("Figma Color & TextStyle Generator (By Node ID)")
    print("=" * 60)
    
    if "figma_token" in FIGMA_TOKEN or "file_key" in FILE_KEY or "node_id" in NODE_ID:
        print("⚠️  WARNING: Please update configuration with actual Token, File Key, and Node ID.")
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(COLORS_OUTPUT) if os.path.dirname(COLORS_OUTPUT) else '.', exist_ok=True)
    os.makedirs(os.path.dirname(TEXTSTYLES_OUTPUT) if os.path.dirname(TEXTSTYLES_OUTPUT) else '.', exist_ok=True)
    
    process_figma_file()
    
    print("\n" + "=" * 60)
    print("✅ All done! Files generated:")
    print(f"   • {COLORS_OUTPUT}")
    print(f"   • {TEXTSTYLES_OUTPUT}")
    print("=" * 60)
