import os
import re

def html_to_jsx(html_content):
    # Basic class to className
    jsx = html_content.replace('class="', 'className="')
    
    # Self-closing tags
    for tag in ['input', 'img', 'br', 'hr', 'link', 'meta']:
        jsx = re.sub(r'(<' + tag + r'[^>]*?)(?<!/)>', r'\1 />', jsx)
        
    # React styles
    jsx = jsx.replace('style="font-variation-settings: \'FILL\' 1;"', "style={{ fontVariationSettings: \"'FILL' 1\" }}")
    jsx = jsx.replace('style="font-variation-settings: \'FILL\' 1"', "style={{ fontVariationSettings: \"'FILL' 1\" }}")
    jsx = jsx.replace('style="width: 65%;"', "style={{ width: '65%' }}")
    jsx = jsx.replace('style="width: 100%;"', "style={{ width: '100%' }}")
    jsx = jsx.replace('selected=""', 'defaultValue="Standard (McCabe > 15)"')
    jsx = jsx.replace('selected', 'defaultValue="Standard (McCabe > 15)"')

    # Fix HTML comments -> JSX comments
    jsx = re.sub(r'<!--(.*?)-->', r'{/*\1*/}', jsx, flags=re.DOTALL)
    
    return jsx

def extract_body_content(html):
    match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""

def generate_page(src_file, target_path, component_name):
    if not os.path.exists(src_file):
        print(f"Not found: {src_file}")
        return
        
    with open(src_file, 'r', encoding='utf-8') as f:
        html = f.read()
        
    body = extract_body_content(html)
    jsx_body = html_to_jsx(body)
    
    # Remove any script elements
    jsx_body = re.sub(r'<script.*?</script>', '', jsx_body, flags=re.DOTALL)
    
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    
    code = f"""'use client'

import React from 'react'
import Link from 'next/link'
import {{ useRouter }} from 'next/navigation'

export default function {component_name}() {{
  const router = useRouter()
  return (
    <div className="min-h-screen bg-surface text-on-surface selection:bg-primary/30 selection:text-primary">
      {jsx_body}
    </div>
  )
}}
"""
    with open(target_path, 'w', encoding='utf-8') as f:
        f.write(code)
    print(f"Generated {target_path}")

# Run the generation
print("Starting generation...")
generate_page('C:/VibeAnalytix/stitch_htmls/landing_page.html', 'C:/VibeAnalytix/frontend/app/page.tsx', 'LandingPage')
generate_page('C:/VibeAnalytix/stitch_htmls/settings.html', 'C:/VibeAnalytix/frontend/app/settings/page.tsx', 'SettingsPage')
generate_page('C:/VibeAnalytix/stitch_htmls/history.html', 'C:/VibeAnalytix/frontend/app/history/page.tsx', 'HistoryPage')
generate_page('C:/VibeAnalytix/stitch_htmls/sign_up.html', 'C:/VibeAnalytix/frontend/app/sign-up/page.tsx', 'SignUpPage')
generate_page('C:/VibeAnalytix/stitch_htmls/forgot_password.html', 'C:/VibeAnalytix/frontend/app/forgot-password/page.tsx', 'ForgotPasswordPage')
print("Done!")
