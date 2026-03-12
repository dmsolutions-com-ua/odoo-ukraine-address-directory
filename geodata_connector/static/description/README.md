# Static Assets

## Required Images

Please add the following images to this directory:

### icon.png
- Size: 128x128 pixels
- Format: PNG
- Description: Module icon displayed in Odoo Apps list

### cover.png
- Size: Recommended 600x300 pixels or similar
- Format: PNG/JPG
- Description: Module cover image for Odoo Apps Store


Example command to create a simple colored placeholder:
```bash
convert -size 128x128 xc:#4CAF50 -pointsize 48 -fill white -gravity center -annotate +0+0 "GD" icon.png
```

Or copy from another module:
```bash
cp ../kw_api_connector/static/description/icon.png ./icon.png
```
