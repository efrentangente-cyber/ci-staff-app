# 📋 COPY-PASTE CODES FOR ANDROID STUDIO

## Complete XML and Resource Files - Ready to Copy!

All Kotlin files are already created. You just need to create these XML files.

---

## 📁 LAYOUT FILES

### 1. activity_splash.xml
**Location**: `app/src/main/res/layout/activity_splash.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<RelativeLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:background="@color/primary"
    android:gravity="center">

    <LinearLayout
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:orientation="vertical"
        android:gravity="center">

        <TextView
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:text="CI STAFF"
            android:textSize="40sp"
            android:textColor="@android:color/white"
            android:textStyle="bold"
            android:letterSpacing="0.1" />

        <TextView
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:text="SYSTEM"
            android:textSize="32sp"
            android:textColor="@android:color/white"
            android:textStyle="bold"
            android:letterSpacing="0.1"
            android:layout_marginTop="8dp" />

        <ProgressBar
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:layout_marginTop="32dp"
            android:indeterminateTint="@android:color/white" />

    </LinearLayout>

</RelativeLayout>
```

---

### 2. activity_login.xml
**Location**: `app/src/main/res/layout/activity_login.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<ScrollView xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:fillViewport="true"
    android:background="@android:color/white">

    <LinearLayout
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:orientation="vertical"
        android:padding="24dp"
        android:gravity="center">

        <TextView
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:text="CI Staff System"
            android:textSize="32sp"
            android:textStyle="bold"
            android:textColor="@color/primary"
            android:layout_marginTop="48dp"
            android:layout_marginBottom="16dp" />

        <TextView
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:text="Login to your account"
            android:textSize="16sp"
            android:textColor="@android:color/darker_gray"
            android:layout_marginBottom="48dp" />

        <com.google.android.material.textfield.TextInputLayout
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginBottom="16dp"
            android:hint="Email"
            style="@style/Widget.MaterialComponents.TextInputLayout.OutlinedBox">

            <com.google.android.material.textfield.TextInputEditText
                android:id="@+id/etEmail"
                android:layout_width="match_parent"
                android:layout_height="wrap_content"
                android:inputType="textEmailAddress"
                android:text="ci@dccco.test" />

        </com.google.android.material.textfield.TextInputLayout>

        <com.google.android.material.textfield.TextInputLayout
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginBottom="24dp"
            android:hint="Password"
            style="@style/Widget.MaterialComponents.TextInputLayout.OutlinedBox"
            app:endIconMode="password_toggle">

            <com.google.android.material.textfield.TextInputEditText
                android:id="@+id/etPassword"
                android:layout_width="match_parent"
                android:layout_height="wrap_content"
                android:inputType="textPassword"
                android:text="ci123" />

        </com.google.android.material.textfield.TextInputLayout>

        <com.google.android.material.button.MaterialButton
            android:id="@+id/btnLogin"
            android:layout_width="match_parent"
            android:layout_height="60dp"
            android:text="Login"
            android:textSize="16sp"
            android:textStyle="bold"
            app:cornerRadius="8dp"
            android:layout_marginBottom="16dp" />

        <TextView
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:text="OR"
            android:textSize="14sp"
            android:textColor="@android:color/darker_gray"
            android:layout_marginTop="8dp"
            android:layout_marginBottom="8dp" />

        <com.google.android.material.button.MaterialButton
            android:id="@+id/btnWebView"
            android:layout_width="match_parent"
            android:layout_height="60dp"
            android:text="Open Web Version"
            android:textSize="16sp"
            app:cornerRadius="8dp"
            style="@style/Widget.MaterialComponents.Button.OutlinedButton" />

        <TextView
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:text="Default Credentials:\nCI Staff: ci@dccco.test / ci123\nAdmin: admin@dccco.test / admin123"
            android:textSize="12sp"
            android:textColor="@android:color/darker_gray"
            android:gravity="center"
            android:layout_marginTop="32dp" />

    </LinearLayout>

</ScrollView>
```

---

### 3. activity_main.xml
**Location**: `app/src/main/res/layout/activity_main.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<androidx.coordinatorlayout.widget.CoordinatorLayout 
    xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto"
    android:layout_width="match_parent"
    android:layout_height="match_parent">

    <com.google.android.material.appbar.AppBarLayout
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:theme="@style/ThemeOverlay.AppCompat.Dark.ActionBar">

        <androidx.appcompat.widget.Toolbar
            android:id="@+id/toolbar"
            android:layout_width="match_parent"
            android:layout_height="?attr/actionBarSize"
            android:background="?attr/colorPrimary"
            app:popupTheme="@style/ThemeOverlay.AppCompat.Light"
            app:title="CI Staff System"
            app:titleTextColor="@android:color/white" />

    </com.google.android.material.appbar.AppBarLayout>

    <FrameLayout
        android:id="@+id/fragmentContainer"
        android:layout_width="match_parent"
        android:layout_height="match_parent"
        app:layout_behavior="@string/appbar_scrolling_view_behavior" />

    <com.google.android.material.bottomnavigation.BottomNavigationView
        android:id="@+id/bottomNavigation"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:layout_gravity="bottom"
        android:background="@android:color/white"
        app:menu="@menu/bottom_nav_menu"
        app:labelVisibilityMode="labeled"
        app:itemIconTint="@color/bottom_nav_color"
        app:itemTextColor="@color/bottom_nav_color" />

</androidx.coordinatorlayout.widget.CoordinatorLayout>
```

---

### 4. activity_webview.xml
**Location**: `app/src/main/res/layout/activity_webview.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:orientation="vertical">

    <androidx.appcompat.widget.Toolbar
        android:id="@+id/toolbar"
        android:layout_width="match_parent"
        android:layout_height="?attr/actionBarSize"
        android:background="?attr/colorPrimary"
        android:theme="@style/ThemeOverlay.AppCompat.Dark.ActionBar"
        app:popupTheme="@style/ThemeOverlay.AppCompat.Light"
        app:title="CI Staff System"
        app:titleTextColor="@android:color/white" />

    <ProgressBar
        android:id="@+id/progressBar"
        android:layout_width="match_parent"
        android:layout_height="4dp"
        android:indeterminate="true"
        android:visibility="gone"
        style="?android:attr/progressBarStyleHorizontal" />

    <WebView
        android:id="@+id/webView"
        android:layout_width="match_parent"
        android:layout_height="match_parent" />

</LinearLayout>
```

---

### 5. fragment_dashboard.xml
**Location**: `app/src/main/res/layout/fragment_dashboard.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<androidx.swiperefreshlayout.widget.SwipeRefreshLayout
    xmlns:android="http://schemas.android.com/apk/res/android"
    android:id="@+id/swipeRefresh"
    android:layout_width="match_parent"
    android:layout_height="match_parent">

    <FrameLayout
        android:layout_width="match_parent"
        android:layout_height="match_parent">

        <androidx.recyclerview.widget.RecyclerView
            android:id="@+id/recyclerViewApplications"
            android:layout_width="match_parent"
            android:layout_height="match_parent"
            android:padding="8dp"
            android:clipToPadding="false" />

        <LinearLayout
            android:id="@+id/tvEmptyState"
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:layout_gravity="center"
            android:orientation="vertical"
            android:gravity="center"
            android:visibility="gone">

            <TextView
                android:layout_width="wrap_content"
                android:layout_height="wrap_content"
                android:text="📋"
                android:textSize="64sp"
                android:layout_marginBottom="16dp" />

            <TextView
                android:layout_width="wrap_content"
                android:layout_height="wrap_content"
                android:text="No applications assigned"
                android:textSize="18sp"
                android:textColor="@android:color/darker_gray"
                android:layout_marginBottom="8dp" />

            <TextView
                android:layout_width="wrap_content"
                android:layout_height="wrap_content"
                android:text="Applications will appear here when assigned to you"
                android:textSize="14sp"
                android:textColor="@android:color/darker_gray"
                android:gravity="center" />

        </LinearLayout>

    </FrameLayout>

</androidx.swiperefreshlayout.widget.SwipeRefreshLayout>
```

---

### 6. fragment_messages.xml
**Location**: `app/src/main/res/layout/fragment_messages.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:gravity="center"
    android:padding="24dp"
    android:orientation="vertical">

    <TextView
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:text="💬"
        android:textSize="64sp"
        android:layout_marginBottom="16dp" />

    <TextView
        android:id="@+id/tvPlaceholder"
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:text="Messages feature coming soon!"
        android:textSize="18sp"
        android:textColor="@android:color/darker_gray"
        android:gravity="center"
        android:layout_marginBottom="8dp" />

    <TextView
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:text="Use WebView for full messaging functionality"
        android:textSize="14sp"
        android:textColor="@android:color/darker_gray"
        android:gravity="center" />

</LinearLayout>
```

---

### 7. fragment_profile.xml
**Location**: `app/src/main/res/layout/fragment_profile.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<ScrollView xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:fillViewport="true">

    <LinearLayout
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:orientation="vertical"
        android:padding="24dp">

        <LinearLayout
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:orientation="vertical"
            android:gravity="center"
            android:padding="24dp"
            android:background="@color/primary"
            android:layout_marginBottom="24dp">

            <TextView
                android:layout_width="wrap_content"
                android:layout_height="wrap_content"
                android:text="👤"
                android:textSize="64sp"
                android:layout_marginBottom="16dp" />

            <TextView
                android:id="@+id/tvUserName"
                android:layout_width="wrap_content"
                android:layout_height="wrap_content"
                android:text="User Name"
                android:textSize="24sp"
                android:textStyle="bold"
                android:textColor="@android:color/white"
                android:layout_marginBottom="8dp" />

            <TextView
                android:id="@+id/tvUserRole"
                android:layout_width="wrap_content"
                android:layout_height="wrap_content"
                android:text="CI Staff"
                android:textSize="16sp"
                android:textColor="@android:color/white"
                android:alpha="0.9" />

        </LinearLayout>

        <TextView
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:text="Account Information"
            android:textSize="18sp"
            android:textStyle="bold"
            android:layout_marginBottom="16dp" />

        <LinearLayout
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:orientation="horizontal"
            android:padding="16dp"
            android:background="@android:color/white"
            android:elevation="2dp"
            android:layout_marginBottom="8dp">

            <TextView
                android:layout_width="0dp"
                android:layout_height="wrap_content"
                android:layout_weight="1"
                android:text="Email"
                android:textSize="14sp"
                android:textColor="@android:color/darker_gray" />

            <TextView
                android:id="@+id/tvUserEmail"
                android:layout_width="wrap_content"
                android:layout_height="wrap_content"
                android:text="user@email.com"
                android:textSize="14sp"
                android:textStyle="bold" />

        </LinearLayout>

        <LinearLayout
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:orientation="horizontal"
            android:padding="16dp"
            android:background="@android:color/white"
            android:elevation="2dp"
            android:layout_marginBottom="8dp">

            <TextView
                android:layout_width="0dp"
                android:layout_height="wrap_content"
                android:layout_weight="1"
                android:text="Role"
                android:textSize="14sp"
                android:textColor="@android:color/darker_gray" />

            <TextView
                android:id="@+id/tvUserRoleDetail"
                android:layout_width="wrap_content"
                android:layout_height="wrap_content"
                android:text="CI Staff"
                android:textSize="14sp"
                android:textStyle="bold" />

        </LinearLayout>

        <TextView
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:text="App Information"
            android:textSize="18sp"
            android:textStyle="bold"
            android:layout_marginTop="24dp"
            android:layout_marginBottom="16dp" />

        <LinearLayout
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:orientation="horizontal"
            android:padding="16dp"
            android:background="@android:color/white"
            android:elevation="2dp"
            android:layout_marginBottom="8dp">

            <TextView
                android:layout_width="0dp"
                android:layout_height="wrap_content"
                android:layout_weight="1"
                android:text="Version"
                android:textSize="14sp"
                android:textColor="@android:color/darker_gray" />

            <TextView
                android:layout_width="wrap_content"
                android:layout_height="wrap_content"
                android:text="1.0.0"
                android:textSize="14sp"
                android:textStyle="bold" />

        </LinearLayout>

    </LinearLayout>

</ScrollView>
```

---

## 📁 VALUES FILES

### 8. strings.xml
**Location**: `app/src/main/res/values/strings.xml`

```xml
<resources>
    <string name="app_name">CI Staff System</string>
    <string name="login">Login</string>
    <string name="email">Email</string>
    <string name="password">Password</string>
    <string name="dashboard">Dashboard</string>
    <string name="messages">Messages</string>
    <string name="profile">Profile</string>
    <string name="logout">Logout</string>
    <string name="web_version">Web Version</string>
    <string name="loading">Loading...</string>
    <string name="error">Error</string>
    <string name="success">Success</string>
    <string name="no_applications">No applications assigned</string>
    <string name="refresh">Refresh</string>
</resources>
```

---

### 9. colors.xml
**Location**: `app/src/main/res/values/colors.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="primary">#6200EE</color>
    <color name="primary_dark">#3700B3</color>
    <color name="primary_light">#BB86FC</color>
    <color name="accent">#03DAC5</color>
    <color name="accent_dark">#018786</color>
    <color name="white">#FFFFFF</color>
    <color name="black">#000000</color>
    <color name="gray">#808080</color>
    <color name="light_gray">#F5F5F5</color>
    <color name="dark_gray">#424242</color>
    <color name="error">#B00020</color>
    <color name="success">#4CAF50</color>
    <color name="warning">#FF9800</color>
</resources>
```

---

### 10. themes.xml
**Location**: `app/src/main/res/values/themes.xml`

```xml
<resources xmlns:tools="http://schemas.android.com/tools">
    <!-- Base application theme -->
    <style name="Theme.CIStaffApp" parent="Theme.MaterialComponents.DayNight.DarkActionBar">
        <!-- Primary brand color -->
        <item name="colorPrimary">@color/primary</item>
        <item name="colorPrimaryVariant">@color/primary_dark</item>
        <item name="colorOnPrimary">@color/white</item>
        <!-- Secondary brand color -->
        <item name="colorSecondary">@color/accent</item>
        <item name="colorSecondaryVariant">@color/accent_dark</item>
        <item name="colorOnSecondary">@color/black</item>
        <!-- Status bar color -->
        <item name="android:statusBarColor">?attr/colorPrimaryVariant</item>
        <!-- Customize your theme here -->
    </style>

    <!-- Splash screen theme -->
    <style name="Theme.CIStaffApp.Splash" parent="Theme.CIStaffApp">
        <item name="android:windowBackground">@color/primary</item>
        <item name="android:windowNoTitle">true</item>
        <item name="android:windowFullscreen">true</item>
        <item name="android:windowContentOverlay">@null</item>
    </style>
</resources>
```

---

### 11. bottom_nav_color.xml
**Location**: `app/src/main/res/color/bottom_nav_color.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<selector xmlns:android="http://schemas.android.com/apk/res/android">
    <item android:color="@color/primary" android:state_checked="true" />
    <item android:color="@color/gray" />
</selector>
```

---

## 📁 MENU FILES

### 12. bottom_nav_menu.xml
**Location**: `app/src/main/res/menu/bottom_nav_menu.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<menu xmlns:android="http://schemas.android.com/apk/res/android">
    <item
        android:id="@+id/nav_dashboard"
        android:icon="@android:drawable/ic_menu_view"
        android:title="@string/dashboard" />
    <item
        android:id="@+id/nav_messages"
        android:icon="@android:drawable/ic_menu_send"
        android:title="@string/messages" />
    <item
        android:id="@+id/nav_profile"
        android:icon="@android:drawable/ic_menu_myplaces"
        android:title="@string/profile" />
</menu>
```

---

### 13. main_menu.xml
**Location**: `app/src/main/res/menu/main_menu.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<menu xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto">
    <item
        android:id="@+id/action_webview"
        android:title="@string/web_version"
        android:icon="@android:drawable/ic_menu_view"
        app:showAsAction="never" />
    <item
        android:id="@+id/action_logout"
        android:title="@string/logout"
        android:icon="@android:drawable/ic_menu_close_clear_cancel"
        app:showAsAction="never" />
</menu>
```

---

## 📁 XML FILES

### 14. backup_rules.xml
**Location**: `app/src/main/res/xml/backup_rules.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<full-backup-content>
    <include domain="sharedpref" path="."/>
    <exclude domain="sharedpref" path="device.xml"/>
</full-backup-content>
```

---

### 15. data_extraction_rules.xml
**Location**: `app/src/main/res/xml/data_extraction_rules.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<data-extraction-rules>
    <cloud-backup>
        <include domain="sharedpref" path="."/>
        <exclude domain="sharedpref" path="device.xml"/>
    </cloud-backup>
    <device-transfer>
        <include domain="sharedpref" path="."/>
        <exclude domain="sharedpref" path="device.xml"/>
    </device-transfer>
</data-extraction-rules>
```

---

### 16. file_paths.xml (FOR CAMERA & GALLERY)
**Location**: `app/src/main/res/xml/file_paths.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<paths xmlns:android="http://schemas.android.com/apk/res/android">
    <!-- External storage for camera photos -->
    <external-files-path 
        name="my_images" 
        path="Pictures" />
    
    <!-- Cache directory for temporary files -->
    <cache-path 
        name="cache" 
        path="." />
    
    <!-- External cache -->
    <external-cache-path 
        name="external_cache" 
        path="." />
</paths>
```

---

## 📁 GRADLE FILES (Already Created)

These files are already in your project:
- ✅ `build.gradle` (project level)
- ✅ `build.gradle` (app level)
- ✅ `settings.gradle`

---

## 🔧 IMPORTANT: Update Server URL

After creating all files, update the server URL in:

**File**: `app/src/main/java/com/dccco/cistaff/network/ApiClient.kt`

```kotlin
// Change this line:
private const val BASE_URL = "http://10.0.2.2:5000/"  // For emulator

// To one of these:
// For real device on same network:
private const val BASE_URL = "http://192.168.10.108:5000/"

// For deployed app:
        private const val BASE_URL = "https://your-app.onrender.com/"
``` 

**Also update in**: `app/src/main/java/com/dccco/cistaff/WebViewActivity.kt`

```kotlin
// Change this line:
val serverUrl = "http://10.0.2.2:5000"

// To:
val serverUrl = "http://192.168.10.108:5000"  // For real device
// or
val serverUrl = "https://your-app.onrender.com"  // For deployed
```

---

## ✅ CHECKLIST

After copying all files:

- [ ] Created all 7 layout XML files
- [ ] Created strings.xml
- [ ] Created colors.xml
- [ ] Created themes.xml
- [ ] Created bottom_nav_color.xml
- [ ] Created 2 menu XML files
- [ ] Created 2 xml folder files
- [ ] Updated server URL in ApiClient.kt
- [ ] Updated server URL in WebViewActivity.kt
- [ ] Synced Gradle
- [ ] Built project
- [ ] Run on emulator/device

---

## 🚀 NEXT STEPS

1. **Create all XML files** (copy-paste from above)
2. **Sync Gradle**: File → Sync Project with Gradle Files
3. **Update server URL** in ApiClient.kt and WebViewActivity.kt
4. **Build project**: Build → Make Project
5. **Run app**: Click Run button (▶️)

---

## 📱 TEST CREDENTIALS

When app opens:
- **Ema