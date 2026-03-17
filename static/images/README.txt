LOGO INSTALLATION INSTRUCTIONS
================================

To complete the logo setup:

1. Save the DCCCO Multipurpose Cooperative logo image as:
   static/images/logo.png

2. The logo should be the circular badge with:
   - Yellow outer ring with "DCCCO MULTIPURPOSE COOPERATIVE"
   - Blue middle ring with "WE CARE"
   - Center image showing hands holding a family
   - "DUMAGUETE CITY" and "1968" text

3. Recommended image specifications:
   - Format: PNG (with transparent background) or JPG
   - Size: 500x500 pixels or larger (square)
   - The template will automatically resize it to fit

4. The logo will appear in:
   - Sidebar header (all authenticated pages)
   - Login page (if you add it there)
   - Mobile app icon (via manifest.json)

Alternative: If you have the logo in a different format (jpg, svg, etc.),
rename the file extension in templates/base.html line 234:
   filename='images/logo.png'  ->  filename='images/logo.jpg'
