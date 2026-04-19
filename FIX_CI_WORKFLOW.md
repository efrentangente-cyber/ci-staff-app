# Fix CI Workflow - Complete Process

## Current Workflow
1. CI Dashboard → Click "Start" → `/ci/application/<id>`
2. Redirects to → `/ci/review/<id>` (Review Page)
3. Click "Fill Interview Checklist" → `/ci/checklist/<id>` (5-Page Wizard)
4. Complete and Submit

## Issues to Fix
1. Error when clicking "Start" button
2. Error when clicking "Fill Interview Checklist"
3. Need to ensure all routes work end-to-end

## Solution: Simplify the Workflow

Remove the intermediate review page and go directly to the wizard:

### Option 1: Direct to Wizard (Simplest)
CI Dashboard → Click "Start" → Wizard (5-page form)

### Option 2: Keep Review Page
CI Dashboard → Click "Start" → Review Page → Click Button → Wizard

## Recommended: Option 1 (Direct to Wizard)

This is the simplest and most reliable approach.

### Changes Needed:
1. Update CI dashboard "Start" button to go directly to wizard
2. Remove intermediate redirects
3. Ensure wizard route works

## Implementation

Update `templates/ci_dashboard.html`:
Change the Start button from:
```html
<a href="{{ url_for('ci_application', id=app.id) }}" class="btn btn-sm btn-warning">
```

To:
```html
<a href="{{ url_for('ci_checklist_wizard', id=app.id) }}" class="btn btn-sm btn-warning">
```

This bypasses all intermediate pages and goes directly to the working wizard.
