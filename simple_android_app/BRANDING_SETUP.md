# DCCCO Android App Branding Setup Guide

## Step 1: Add DCCCO Logo to Android Studio

1. Open your Android Studio project
2. Copy the DCCCO logo from `static/images/logo.jpg`
3. In Android Studio, navigate to: `app/src/main/res/drawable/`
4. Paste the logo and rename it to `logo.png` (or keep as `logo.jpg`)

## Step 2: Add Resource Files

Copy these files to your Android Studio project:

### Colors (app/src/main/res/values/colors.xml)
- Copy `simple_android_app/colors.xml` to `app/src/main/res/values/colors.xml`

### Themes (app/src/main/res/values/themes.xml)
- Copy `simple_android_app/themes.xml` to `app/src/main/res/values/themes.xml`

### Splash Screen (app/src/main/res/drawable/splash_screen.xml)
- Copy `simple_android_app/splash_screen.xml` to `app/src/main/res/drawable/splash_screen.xml`

## Step 3: Update AndroidManifest.xml

The AndroidManifest.xml has already been updated with:
- App name: "DCCCO CI Staff"
- Theme: AppTheme (DCCCO colors)
- Splash screen theme

## Step 4: Create App Icon with DCCCO Logo

1. In Android Studio, right-click on `res` folder
2. Select `New > Image Asset`
3. Choose "Launcher Icons (Adaptive and Legacy)"
4. Click on the path field and select your DCCCO logo
5. Adjust the trim and resize as needed
6. Click "Next" then "Finish"

## Step 5: Update MainActivity (Optional - Add Splash Screen)

Add this to the beginning of your MainActivity.kt onCreate method:

```kotlin
override fun onCreate(savedInstanceState: Bundle?) {
    // Switch back to AppTheme after splash
    setTheme(R.style.AppTheme)
    super.onCreate(savedInstanceState)
    // ... rest of your code
}
```

## Step 6: Rebuild and Install

1. In Android Studio: `Build > Clean Project`
2. Then: `Build > Rebuild Project`
3. Connect your device
4. Click the green "Run" button

## Result

Your app will now have:
- ✅ DCCCO logo as app icon
- ✅ DCCCO blue (#1e3a5f) and yellow (#fbbf24) brand colors
- ✅ Custom splash screen with DCCCO logo
- ✅ App name: "DCCCO CI Staff"
- ✅ Professional branded appearance

## Troubleshooting

If the logo doesn't appear:
1. Make sure the logo file is in `app/src/main/res/drawable/`
2. The filename should be lowercase with no spaces (e.g., `logo.png`)
3. Clean and rebuild the project
4. Uninstall the old app from your device before installing the new one
