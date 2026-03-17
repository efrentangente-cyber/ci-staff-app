# Camera & Gallery Setup Guide for DCCCO Android App

## What's Been Added

### 1. Permissions (AndroidManifest.xml)
- `CAMERA` - Access device camera
- `READ_EXTERNAL_STORAGE` - Read images from gallery (Android 12 and below)
- `WRITE_EXTERNAL_STORAGE` - Save camera photos (Android 12 and below)
- `READ_MEDIA_IMAGES` - Read images (Android 13+)

### 2. File Upload Functionality (MainActivity.kt)
- **WebChromeClient** with file chooser support
- **Camera capture** - Take photos directly
- **Gallery selection** - Choose existing photos
- **Multiple file selection** - Select multiple images at once
- **FileProvider** - Secure file sharing between app and camera

### 3. File Provider Configuration
- `file_paths.xml` - Defines accessible directories
- FileProvider in manifest - Enables secure file URI sharing

## How It Works

When user clicks "Choose File" button:
1. App shows chooser dialog with options:
   - **Take Photo** (opens camera)
   - **Choose from Gallery** (opens gallery)
   - **Files** (file manager)

2. User can:
   - Take a new photo with camera
   - Select one or multiple photos from gallery
   - Browse files

3. Selected files are uploaded to the web form

## Build Requirements

### build.gradle (Module: app)
Make sure you have these dependencies:

```gradle
dependencies {
    implementation 'androidx.core:core-ktx:1.12.0'
    implementation 'androidx.appcompat:appcompat:1.6.1'
    implementation 'com.google.android.material:material:1.11.0'
}
```

### Minimum SDK
- minSdkVersion: 24 (Android 7.0)
- targetSdkVersion: 34 (Android 14)

## Testing

### On Emulator
1. Make sure emulator has camera enabled
2. Use emulator's virtual camera or webcam
3. Gallery will have sample images

### On Real Device
1. Install APK on device
2. Grant camera and storage permissions when prompted
3. Test both camera and gallery selection

## File Locations

```
simple_android_app/
├── AndroidManifest.xml          # Permissions & FileProvider
├── MainActivity.kt              # File upload logic
├── file_paths.xml              # FileProvider paths (put in res/xml/)
└── CAMERA_SETUP.md             # This guide
```

## Important Notes

1. **FileProvider Path**: The `file_paths.xml` must be placed in `res/xml/` directory in Android Studio
2. **Package Name**: FileProvider uses `${applicationId}.fileprovider` which automatically uses your package name
3. **Permissions**: App requests permissions at runtime on first launch
4. **Multiple Selection**: Users can select multiple images from gallery
5. **Image Format**: Only image files (image/*) are accepted

## Troubleshooting

### Camera not opening
- Check CAMERA permission is granted
- Verify device has camera hardware
- Check FileProvider is properly configured

### Gallery not showing images
- Check READ_EXTERNAL_STORAGE or READ_MEDIA_IMAGES permission
- Verify images exist in device gallery

### File upload not working
- Check internet connection
- Verify server accepts multipart/form-data
- Check file size limits on server

## Next Steps in Android Studio

1. Copy `file_paths.xml` to `app/src/main/res/xml/` directory
2. If `xml` folder doesn't exist, create it
3. Sync Gradle files
4. Build and run the app
5. Test camera and gallery functionality

## Server-Side (Already Configured)

The web form already has:
- `accept="image/*"` - Accept only images
- `multiple` attribute - Allow multiple file selection
- File upload handling in Flask backend

No changes needed on server side!
