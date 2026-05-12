package com.example.myci;

import android.Manifest;
import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.graphics.Rect;
import android.net.ConnectivityManager;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.provider.MediaStore;
import android.webkit.GeolocationPermissions;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.CookieManager;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import androidx.annotation.RequiresApi;
import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.appcompat.app.AlertDialog;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.content.ContextCompat;
import androidx.core.content.FileProvider;

import com.example.myci.web.WebAppIntents;
import com.example.myci.web.WebSessionSync;
import android.view.KeyEvent;
import android.view.Menu;
import android.view.MenuItem;
import android.view.View;
import android.view.ViewTreeObserver;
import android.widget.LinearLayout;
import android.widget.RelativeLayout;
import android.widget.Toast;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.text.SimpleDateFormat;
import java.nio.charset.StandardCharsets;
import java.util.Date;
import java.util.Locale;

public class MainActivity extends AppCompatActivity {

    /** Base URL from {@link R.string#webapp_base_url} — same origin as server for IndexedDB offline. */
    private String productionApp;
    private String productionOrigin;

    private WebView webView;
    private boolean isDesktopMode = false;
    private ValueCallback<Uri[]> filePathCallback;
    private Uri cameraImageUri;
    private LinearLayout loadingScreen;

    /**
     * When offline, the first main-frame error for an interview URL is often a network error before
     * the WebView uses the HTTP cache. Retry once with {@link WebSettings#LOAD_CACHE_ONLY} so a
     * page opened at least once online can still load.
     */
    private int ciApplicationCacheRetryStep;

    /** After the first page has painted, hide the splash immediately on new navigations (no full-screen wait). */
    private boolean webContentHasCommitted;

    /**
     * When the device goes offline, cached {@code /ci/dashboard} can still show — user wants the
     * dedicated offline shell ({@code /ci/offline_shell}) instead of that full Assigned Applications page.
     */
    private ConnectivityManager connectivityManager;
    private ConnectivityManager.NetworkCallback connectivityNetworkCallback;

    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    /** Debounce: onGlobalLayout fires often; avoid spamming {@code evaluateJavascript} during IME animation. */
    private Runnable keyboardHeightNotifyRunnable;
    /** Delay before switching dashboard → offline shell so brief Wi‑Fi drops don’t interrupt the user (~0.9s). */
    private Runnable deferredOfflineShellRunnable;

    /** Single-pass layout fix (avoid 2–3 separate {@code evaluateJavascript} round-trips per page). */
    private static final String JS_MIN_BODY =
            "document.body.style.height='100%';document.body.style.minHeight='100vh';"
                    + "document.body.style.overflow='auto';document.documentElement.style.height='100%';";

    private static final String JS_MIN_VIEWPORT = "(function(){" + JS_MIN_BODY + "})()";

    /** Dashboard: viewport fix + compact stat-card CSS in one bridge call */
    private static final String JS_DASHBOARD_AND_VIEWPORT =
            "(function(){"
                    + JS_MIN_BODY
                    + "var st=document.createElement('style');"
                    + "st.innerHTML='.stats-grid{grid-template-columns:repeat(2,1fr)!important;gap:8px!important;"
                    + "margin-bottom:12px!important;}.stat-card{padding:10px 12px!important;}.stat-card h3{font-size:20px!important;}"
                    + ".stat-card p{font-size:11px!important;margin:2px 0 0 0!important;}.stat-card-icon{width:32px!important;height:32px!important;"
                    + "font-size:16px!important;margin-bottom:8px!important;}';document.head.appendChild(st);})()";

    /** Messages: viewport + messenger tweaks in one bridge call */
    private static final String JS_MESSAGES_AND_VIEWPORT =
            "(function(){"
                    + JS_MIN_BODY
                    + "var style=document.createElement('style');"
                    + "style.innerHTML='.messenger-dark-container{height:calc(100% - 130px)!important;position:relative!important;}"
                    + ".conversations-sidebar{width:100%!important;height:100%!important;}"
                    + ".chat-main-panel{position:absolute!important;top:0!important;left:0!important;right:0!important;bottom:0!important;"
                    + "z-index:10!important;display:none!important;background:white!important;}"
                    + ".chat-main-panel.active{display:flex!important;flex-direction:column!important;}"
                    + ".active-chat{display:flex!important;flex-direction:column!important;height:100%!important;}"
                    + ".messages-container{flex:1!important;overflow-y:auto!important;min-height:0!important;}"
                    + ".message-input-container{flex-shrink:0!important;background:white!important;z-index:9999!important;}"
                    + ".chat-header-bar::before{content:none!important;}.back-btn{display:flex!important;}';document.head.appendChild(style);"
                    + "var o=window.loadChat;window.loadChat=function(uid,uname,role){if(typeof o==='function')o(uid,uname,role);"
                    + "var p=document.querySelector('.chat-main-panel');if(p)p.classList.add('active');"
                    + "var h=document.querySelector('.chat-header-bar');"
                    + "if(h&&!document.getElementById('backBtn')){var btn=document.createElement('button');btn.id='backBtn';"
                    + "btn.innerHTML='<i class=\\\"bi bi-arrow-left\\\"></i>';"
                    + "btn.style.cssText='background:none;border:none;font-size:20px;color:#1e3a5f;margin-right:10px;cursor:pointer;';"
                    + "btn.onclick=function(){var x=document.querySelector('.chat-main-panel');if(x)x.classList.remove('active');};"
                    + "h.insertBefore(btn,h.firstChild);}};"
                    + "function fixInputPosition(){var vv=window.visualViewport;if(!vv)return;var input=document.querySelector('.message-input-container');"
                    + "var msgs=document.getElementById('messagesContainer');if(!input)return;var inputH=input.offsetHeight||64;"
                    + "var topPos=vv.offsetTop+vv.height-inputH;input.style.position='fixed';input.style.top=topPos+'px';input.style.bottom='auto';"
                    + "input.style.left='0';input.style.right='0';input.style.zIndex='99999';input.style.background='white';"
                    + "input.style.borderTop='1px solid #e5e7eb';if(msgs){msgs.style.paddingBottom=(inputH+8)+'px';msgs.scrollTop=msgs.scrollHeight;}}"
                    + "if(window.visualViewport){window.visualViewport.addEventListener('resize',fixInputPosition);"
                    + "window.visualViewport.addEventListener('scroll',fixInputPosition);}})()";

    private final ActivityResultLauncher<String[]> locationPermissionLauncher =
            registerForActivityResult(new ActivityResultContracts.RequestMultiplePermissions(), r -> { });

    private final ActivityResultLauncher<String[]> cameraPermissionLauncher =
            registerForActivityResult(new ActivityResultContracts.RequestMultiplePermissions(), result -> {
                if (Boolean.TRUE.equals(result.get(Manifest.permission.CAMERA))) {
                    openCamera();
                }
            });
    
    private final ActivityResultLauncher<Intent> galleryLauncher =
            registerForActivityResult(new ActivityResultContracts.StartActivityForResult(), result -> {
                if (filePathCallback == null) return;
                
                Uri[] results = null;
                if (result.getResultCode() == Activity.RESULT_OK && result.getData() != null) {
                    Intent data = result.getData();
                    
                    // Check if multiple images were selected
                    if (data.getClipData() != null) {
                        int count = data.getClipData().getItemCount();
                        results = new Uri[count];
                        for (int i = 0; i < count; i++) {
                            results[i] = data.getClipData().getItemAt(i).getUri();
                        }
                    } else if (data.getData() != null) {
                        // Single image selected
                        results = new Uri[]{data.getData()};
                    }
                }
                filePathCallback.onReceiveValue(results);
                filePathCallback = null;
            });
    
    private final ActivityResultLauncher<Intent> cameraLauncher =
            registerForActivityResult(new ActivityResultContracts.StartActivityForResult(), result -> {
                if (filePathCallback == null) return;
                
                Uri[] results = null;
                if (result.getResultCode() == Activity.RESULT_OK && cameraImageUri != null) {
                    results = new Uri[]{cameraImageUri};
                }
                filePathCallback.onReceiveValue(results);
                filePathCallback = null;
                cameraImageUri = null;
            });

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        com.google.android.material.appbar.MaterialToolbar toolbar = findViewById(R.id.toolbar);
        setSupportActionBar(toolbar);

        String base = getString(R.string.webapp_base_url).trim();
        while (base.endsWith("/")) {
            base = base.substring(0, base.length() - 1);
        }
        productionApp = base;
        productionOrigin = base + "/";

        webView = findViewById(R.id.webView);
        loadingScreen = findViewById(R.id.loadingScreen);
        webView.setLayerType(View.LAYER_TYPE_HARDWARE, null);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            // Prefer IMPORTANT over BOUND so Chromium keeps a higher-priority renderer (snappier nav/scroll).
            webView.setRendererPriorityPolicy(WebView.RENDERER_PRIORITY_IMPORTANT, true);
        }

        // Persist session cookies so logged-in PWA / fetch(..., { credentials: 'include' }) works after relaunch
        CookieManager.getInstance().setAcceptCookie(true);
        CookieManager.getInstance().setAcceptThirdPartyCookies(webView, true);

        // Native keyboard height detector — posts keyboard height into WebView JS
        RelativeLayout rootLayout = findViewById(R.id.rootLayout);
        rootLayout.getViewTreeObserver().addOnGlobalLayoutListener(new ViewTreeObserver.OnGlobalLayoutListener() {
            private int lastKeyboardHeightPx = -1;

            @Override
            public void onGlobalLayout() {
                Rect r = new Rect();
                rootLayout.getWindowVisibleDisplayFrame(r);
                int screenHeight = rootLayout.getRootView().getHeight();
                int keyboardHeight = screenHeight - r.bottom;
                if (keyboardHeight < 100) {
                    keyboardHeight = 0;
                }
                if (keyboardHeight == lastKeyboardHeightPx) {
                    return;
                }
                lastKeyboardHeightPx = keyboardHeight;
                if (keyboardHeightNotifyRunnable != null) {
                    mainHandler.removeCallbacks(keyboardHeightNotifyRunnable);
                }
                final int kh = keyboardHeight;
                keyboardHeightNotifyRunnable = () -> {
                    keyboardHeightNotifyRunnable = null;
                    webView.evaluateJavascript(
                            "(function(){var kh=" + kh + ";var n=document.querySelector('.bottom-nav');"
                                    + "if(!document.getElementById('kbFixStyle')){var s=document.createElement('style');"
                                    + "s.id='kbFixStyle';s.innerHTML='.kb-open{display:none!important;}';document.head.appendChild(s);}"
                                    + "if(kh>0){if(n)n.classList.add('kb-open');}else{if(n)n.classList.remove('kb-open');}})()",
                            null);
                };
                mainHandler.postDelayed(keyboardHeightNotifyRunnable, 16);
            }
        });
        
        // Location: ask after first layout pass so initial WebView load isn't blocked by the system dialog.
        rootLayout.post(() -> {
            if (ContextCompat.checkSelfPermission(MainActivity.this, Manifest.permission.ACCESS_FINE_LOCATION)
                    != PackageManager.PERMISSION_GRANTED) {
                locationPermissionLauncher.launch(new String[]{
                    Manifest.permission.ACCESS_FINE_LOCATION,
                    Manifest.permission.ACCESS_COARSE_LOCATION
                });
            }
        });

        // Force WebView to fill entire screen
        webView.setScrollBarStyle(WebView.SCROLLBARS_OUTSIDE_OVERLAY);
        webView.setScrollbarFadingEnabled(false);

        // Configure WebView settings
        webView.setWebViewClient(new WebViewClient() {
            @Override
            public void onPageStarted(WebView view, String url, Bitmap favicon) {
                super.onPageStarted(view, url, favicon);
                if (webContentHasCommitted) {
                    loadingScreen.setVisibility(View.GONE);
                }
            }

            @RequiresApi(api = Build.VERSION_CODES.M)
            @Override
            public void onPageCommitVisible(WebView view, String url) {
                super.onPageCommitVisible(view, url);
                webContentHasCommitted = true;
                loadingScreen.setVisibility(View.GONE);
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                ciApplicationCacheRetryStep = 0;
                view.getSettings().setCacheMode(WebSettings.LOAD_DEFAULT);
                webContentHasCommitted = true;
                loadingScreen.setVisibility(View.GONE);
                injectPostLoadHelpers(view, url);
                // Avoid flush here: disk I/O after every navigate slows SPA transitions.
                // onPause still flushes so cookies persist when switching apps / backgrounding.
            }

            /**
             * Route-specific tweaks only. Previously every {@code /ci/*} page ran the full messenger
             * script (expensive); that is limited to {@code /messages} now. Dashboard stats CSS only on
             * {@code /ci/dashboard}. Uses {@link WebView#evaluateJavascript} instead of {@code loadUrl(javascript:…)}.
             */
            private void injectPostLoadHelpers(WebView view, String url) {
                if (url == null || url.isEmpty()) {
                    return;
                }
                String u = url.toLowerCase(Locale.ROOT);
                String path = null;
                try {
                    path = Uri.parse(url).getPath();
                } catch (Exception ignored) {
                }
                if (path != null) {
                    path = path.toLowerCase(Locale.ROOT);
                }

                boolean appShellPage = u.contains("/ci/") || u.contains("/messages") || u.contains("/login");
                if (!appShellPage) {
                    return;
                }

                if (path != null && path.contains("/messages")) {
                    view.evaluateJavascript(JS_MESSAGES_AND_VIEWPORT, null);
                } else if (path != null && path.contains("/ci/dashboard")) {
                    view.evaluateJavascript(JS_DASHBOARD_AND_VIEWPORT, null);
                } else {
                    view.evaluateJavascript(JS_MIN_VIEWPORT, null);
                }
            }

            /**
             * Only fall back to offline shell for the main document. Subresource failures (CDN, etc.)
             * must not replace the whole page — that was breaking the live app in WebView.
             */
            @SuppressWarnings("deprecation")
            @Override
            public void onReceivedError(WebView view, int errorCode, String description, String failingUrl) {
                if (Build.VERSION.SDK_INT < Build.VERSION_CODES.M) {
                    loadingScreen.setVisibility(View.GONE);
                    handleMainFrameLoadError(view, failingUrl);
                }
            }

            @RequiresApi(api = Build.VERSION_CODES.M)
            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request != null && request.isForMainFrame()) {
                    loadingScreen.setVisibility(View.GONE);
                    String failingUrl = request.getUrl() != null ? request.getUrl().toString() : null;
                    handleMainFrameLoadError(view, failingUrl);
                }
            }
        });
        
        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView webView, ValueCallback<Uri[]> filePathCallback,
                                            FileChooserParams fileChooserParams) {
                if (MainActivity.this.filePathCallback != null) {
                    MainActivity.this.filePathCallback.onReceiveValue(null);
                }
                MainActivity.this.filePathCallback = filePathCallback;
                showFileChooserDialog();
                return true;
            }

            @Override
            public void onGeolocationPermissionsShowPrompt(String origin, GeolocationPermissions.Callback callback) {
                // Auto-grant geolocation to the app's origin
                callback.invoke(origin, true, false);
            }
        });

        WebSettings webSettings = webView.getSettings();
        webSettings.setJavaScriptEnabled(true);
        webSettings.setDomStorageEnabled(true);
        webSettings.setGeolocationEnabled(true);
        webSettings.setCacheMode(WebSettings.LOAD_DEFAULT);

        // Mobile viewport settings - allow horizontal scrolling for wide content
        webSettings.setUseWideViewPort(true);
        webSettings.setLoadWithOverviewMode(true);
        webSettings.setSupportZoom(true);
        webSettings.setBuiltInZoomControls(true);
        webSettings.setDisplayZoomControls(false);
        
        webView.setHorizontalScrollBarEnabled(true);
        webView.addJavascriptInterface(new OfflineFolderBridge(this), "MyCiOfflineFolder");

        // Additional settings for better compatibility
        webSettings.setAllowFileAccess(true);
        webSettings.setAllowContentAccess(true);
        webSettings.setLoadsImagesAutomatically(true);
        webSettings.setJavaScriptCanOpenWindowsAutomatically(true);
        
        // Set mobile user agent by default
        setUserAgent(false);

        webSettings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            webSettings.setSafeBrowsingEnabled(false);
        }

        registerConnectivityForOfflineShell();
        startWebContentNavigation();
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        if (webView != null) {
            webContentHasCommitted = false;
            startWebContentNavigation();
        }
    }

    /**
     * Start navigation immediately (no blocking HTTP ping — that could delay up to 30s before
     * {@code loadUrl}). When the device has no network, open the offline shell directly so the
     * UI appears without waiting for connection timeouts.
     * <p>
     * Supports {@link WebAppIntents}: optional path under the production base and optional
     * native→web session bridge via {@link WebSessionSync}.
     */
    private String normalizeWebPathExtra(String raw) {
        if (raw == null) {
            return null;
        }
        String p = raw.trim();
        if (p.isEmpty()) {
            return null;
        }
        if (!p.startsWith("/")) {
            p = "/" + p;
        }
        if (p.startsWith("//")) {
            return null;
        }
        return p;
    }

    private void startWebContentNavigation() {
        if (webView == null) {
            return;
        }
        Intent intent = getIntent();
        String webPathRaw = intent.getStringExtra(WebAppIntents.EXTRA_WEB_PATH);
        boolean bridgeSession = intent.getBooleanExtra(WebAppIntents.EXTRA_BRIDGE_SESSION, false);
        String normalizedPath = normalizeWebPathExtra(webPathRaw);

        if (!seemsOnline()) {
            loadOfflineDashboardInWebView(webView);
            return;
        }

        if (bridgeSession && normalizedPath != null) {
            loadingScreen.setVisibility(View.VISIBLE);
            final String pathForBridge = normalizedPath;
            new Thread(() -> {
                WebSessionSync.bridgeIfPossible(MainActivity.this, productionApp, pathForBridge);
                final String target = productionApp + pathForBridge;
                mainHandler.post(() -> webView.loadUrl(target));
            }, "myci-session-bridge").start();
        } else if (bridgeSession) {
            loadingScreen.setVisibility(View.VISIBLE);
            new Thread(() -> {
                WebSessionSync.bridgeIfPossible(MainActivity.this, productionApp, "/");
                mainHandler.post(() -> webView.loadUrl(productionApp));
            }, "myci-session-bridge").start();
        } else if (normalizedPath != null) {
            webView.loadUrl(productionApp + normalizedPath);
        } else {
            webView.loadUrl(productionApp);
        }
    }

    /**
     * If the OS reports loss of connectivity while the WebView is showing cached
     * {@code .../ci/dashboard}, navigate to {@code /ci/offline_shell} so CI staff stay on the
     * bundled offline dashboard (Start → offline checklist) instead of the full PWA list.
     */
    private void registerConnectivityForOfflineShell() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.N) {
            return;
        }
        connectivityManager = (ConnectivityManager) getSystemService(Context.CONNECTIVITY_SERVICE);
        if (connectivityManager == null) {
            return;
        }
        connectivityNetworkCallback = new ConnectivityManager.NetworkCallback() {
            @Override
            public void onAvailable(Network network) {
                runOnUiThread(() -> {
                    if (deferredOfflineShellRunnable != null) {
                        mainHandler.removeCallbacks(deferredOfflineShellRunnable);
                        deferredOfflineShellRunnable = null;
                    }
                });
            }

            @Override
            public void onLost(Network network) {
                runOnUiThread(() -> {
                    if (deferredOfflineShellRunnable != null) {
                        mainHandler.removeCallbacks(deferredOfflineShellRunnable);
                    }
                    deferredOfflineShellRunnable = () -> {
                        deferredOfflineShellRunnable = null;
                        if (!seemsOnline()) {
                            leaveCachedCiDashboardWhenOffline();
                        }
                    };
                    mainHandler.postDelayed(deferredOfflineShellRunnable, 900);
                });
            }
        };
        connectivityManager.registerDefaultNetworkCallback(connectivityNetworkCallback);
    }

    /** Rough online check — after {@code NetworkCallback#onLost}, another transport may still exist. */
    private boolean seemsOnline() {
        if (connectivityManager == null) {
            connectivityManager = (ConnectivityManager) getSystemService(Context.CONNECTIVITY_SERVICE);
        }
        if (connectivityManager == null) {
            return true;
        }
        Network active = connectivityManager.getActiveNetwork();
        if (active == null) {
            return false;
        }
        NetworkCapabilities caps = connectivityManager.getNetworkCapabilities(active);
        return caps != null && caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET);
    }

    private void leaveCachedCiDashboardWhenOffline() {
        if (webView == null || seemsOnline()) {
            return;
        }
        String url = webView.getUrl();
        if (url == null) {
            return;
        }
        try {
            String path = Uri.parse(url).getPath();
            if (path == null) {
                return;
            }
            String pl = path.toLowerCase(Locale.ROOT);
            if (pl.startsWith("/ci/dashboard")) {
                loadOfflineDashboardInWebView(webView);
            }
        } catch (Exception ignored) {
        }
    }

    @Override
    protected void onDestroy() {
        if (keyboardHeightNotifyRunnable != null) {
            mainHandler.removeCallbacks(keyboardHeightNotifyRunnable);
            keyboardHeightNotifyRunnable = null;
        }
        if (deferredOfflineShellRunnable != null) {
            mainHandler.removeCallbacks(deferredOfflineShellRunnable);
            deferredOfflineShellRunnable = null;
        }
        if (!isChangingConfigurations() && webView != null) {
            try {
                webView.evaluateJavascript(
                        "(function(){try{if(typeof window.__myciOnAppClose==='function')window.__myciOnAppClose();}catch(e){}})()",
                        null);
            } catch (Exception ignored) {
            }
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N && connectivityManager != null
                && connectivityNetworkCallback != null) {
            try {
                connectivityManager.unregisterNetworkCallback(connectivityNetworkCallback);
            } catch (Exception ignored) {
            }
            connectivityNetworkCallback = null;
        }
        super.onDestroy();
    }

    @Override
    protected void onResume() {
        super.onResume();
        leaveCachedCiDashboardWhenOffline();
    }

    /** Persist cookies to disk when leaving the activity (photos, OTP apps, multitasking). */
    @Override
    protected void onPause() {
        super.onPause();
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            CookieManager.getInstance().flush();
        }
    }

    // Handle back button to navigate within WebView
    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (keyCode == KeyEvent.KEYCODE_BACK && webView.canGoBack()) {
            webView.goBack();
            return true;
        }
        return super.onKeyDown(keyCode, event);
    }

    // Create options menu
    @Override
    public boolean onCreateOptionsMenu(Menu menu) {
        getMenuInflater().inflate(R.menu.main_menu, menu);
        return true;
    }

    // Handle menu item clicks
    @Override
    public boolean onOptionsItemSelected(MenuItem item) {
        int id = item.getItemId();
        
        if (id == R.id.action_toggle_view) {
            toggleViewMode();
            return true;
        } else if (id == R.id.action_refresh) {
            webView.reload();
            Toast.makeText(this, "Refreshing...", Toast.LENGTH_SHORT).show();
            return true;
        } else if (id == R.id.action_native_mode) {
            startActivity(new Intent(this, com.example.myci.ui.LoginActivity.class));
            return true;
        }

        return super.onOptionsItemSelected(item);
    }

    private boolean isCiApplicationPath(String url) {
        if (url == null || url.isEmpty()) {
            return false;
        }
        try {
            String p = Uri.parse(url).getPath();
            if (p == null) {
                return false;
            }
            String pl = p.toLowerCase(Locale.ROOT);
            return pl.contains("/ci/application/");
        } catch (Exception ignored) {
            return false;
        }
    }

    /** Main-frame load failure: retry interview from HTTP cache once; else offline shell (server or bundled asset fallback). */
    private void handleMainFrameLoadError(WebView view, String failingUrl) {
        if (failingUrl != null && failingUrl.contains("/ci/offline_shell")) {
            loadOfflineDashboardEmbeddedFallback(view);
            return;
        }
        if (isCiApplicationPath(failingUrl) && ciApplicationCacheRetryStep == 0) {
            ciApplicationCacheRetryStep = 1;
            view.getSettings().setCacheMode(WebSettings.LOAD_CACHE_ONLY);
            view.loadUrl(failingUrl);
            return;
        }
        if (isCiApplicationPath(failingUrl) && ciApplicationCacheRetryStep == 1) {
            Toast.makeText(
                    this,
                    "This interview is not in cache. Open it once while online, then you can use it offline.",
                    Toast.LENGTH_LONG
            ).show();
        }
        ciApplicationCacheRetryStep = 0;
        view.getSettings().setCacheMode(WebSettings.LOAD_DEFAULT);
        loadOfflineDashboardInWebView(view);
    }

    /**
     * Load server-hosted offline shell ({@code /ci/offline_shell}) so cookies match the API origin.
     * If the network fails, {@link #handleMainFrameLoadError} falls back to embedded HTML.
     */
    private void loadOfflineDashboardInWebView(WebView view) {
        view.loadUrl(productionApp + "/ci/offline_shell");
    }

    /**
     * Embedded offline.html — used when {@code /ci/offline_shell} cannot be reached (pure offline).
     */
    private void loadOfflineDashboardEmbeddedFallback(WebView view) {
        try {
            String html = injectAppBaseOriginMeta(readAssetFileAsString("offline.html"));
            view.loadDataWithBaseURL(
                    productionOrigin,
                    html,
                    "text/html",
                    "utf-8",
                    productionOrigin
            );
        } catch (IOException e) {
            Toast.makeText(
                    this,
                    "Could not read offline.html; opening online shell instead.",
                    Toast.LENGTH_LONG
            ).show();
            view.loadUrl(productionApp + "/ci/offline_shell");
        }
    }

    /**
     * Asset HTML has no reliable {@code location} for API calls. Inject the same host as
     * {@link R.string#webapp_base_url} so JS {@code fetch} hits your Flask server (session cookies + POST).
     */
    private String injectAppBaseOriginMeta(String html) {
        if (html == null || html.isEmpty()) {
            return html;
        }
        String escaped = productionApp.replace("&", "&amp;").replace("\"", "&quot;");
        String meta = "<meta name=\"app-base-origin\" content=\"" + escaped + "\" />";
        int i = html.indexOf("<head>");
        if (i >= 0) {
            int after = i + "<head>".length();
            return html.substring(0, after) + meta + html.substring(after);
        }
        return meta + html;
    }

    private String readAssetFileAsString(String assetName) throws IOException {
        try (InputStream is = getAssets().open(assetName);
             ByteArrayOutputStream baos = new ByteArrayOutputStream()) {
            byte[] buf = new byte[4096];
            int n;
            while ((n = is.read(buf)) != -1) {
                baos.write(buf, 0, n);
            }
            return baos.toString(StandardCharsets.UTF_8.name());
        }
    }

    // Toggle between mobile and desktop view
    private void toggleViewMode() {
        isDesktopMode = !isDesktopMode;
        setUserAgent(isDesktopMode);
        webView.reload();
        
        String mode = isDesktopMode ? "Desktop" : "Mobile";
        Toast.makeText(this, mode + " view enabled", Toast.LENGTH_SHORT).show();
    }

    // Set user agent based on mode
    private void setUserAgent(boolean desktop) {
        WebSettings webSettings = webView.getSettings();
        if (desktop) {
            // Desktop user agent
            webSettings.setUserAgentString("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36");
            webSettings.setUseWideViewPort(true);
            webSettings.setLoadWithOverviewMode(true);
            webView.setInitialScale(1);
        } else {
            // Mobile user agent
            webSettings.setUserAgentString(null); // Use default mobile user agent
            webSettings.setUseWideViewPort(true);
            webSettings.setLoadWithOverviewMode(true);
        }
    }
    
    // Show dialog to choose between camera and gallery
    private void showFileChooserDialog() {
        AlertDialog.Builder builder = new AlertDialog.Builder(this);
        builder.setTitle("Choose Image Source");
        builder.setItems(new CharSequence[]{"Camera", "Gallery"}, (dialog, which) -> {
            if (which == 0) {
                checkCameraPermissionAndOpen();
            } else {
                openGallery();
            }
        });
        builder.setOnCancelListener(dialog -> {
            if (filePathCallback != null) {
                filePathCallback.onReceiveValue(null);
                filePathCallback = null;
            }
        });
        builder.show();
    }
    
    // Check camera permission
    private void checkCameraPermissionAndOpen() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
                != PackageManager.PERMISSION_GRANTED) {
            cameraPermissionLauncher.launch(new String[]{Manifest.permission.CAMERA});
        } else {
            openCamera();
        }
    }
    
    // Open camera
    private void openCamera() {
        Intent takePictureIntent = new Intent(MediaStore.ACTION_IMAGE_CAPTURE);
        if (takePictureIntent.resolveActivity(getPackageManager()) != null) {
            File photoFile = null;
            try {
                photoFile = createImageFile();
            } catch (IOException ex) {
                Toast.makeText(this, "Error creating image file", Toast.LENGTH_SHORT).show();
            }
            
            if (photoFile != null) {
                cameraImageUri = FileProvider.getUriForFile(this,
                        "com.example.myci.fileprovider", photoFile);
                takePictureIntent.putExtra(MediaStore.EXTRA_OUTPUT, cameraImageUri);
                cameraLauncher.launch(takePictureIntent);
            }
        }
    }
    
    // Open gallery
    private void openGallery() {
        Intent intent = new Intent(Intent.ACTION_PICK);
        intent.setType("image/*");
        intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true);
        galleryLauncher.launch(intent);
    }
    
    // Create image file for camera
    private File createImageFile() throws IOException {
        String timeStamp = new SimpleDateFormat("yyyyMMdd_HHmmss", Locale.getDefault()).format(new Date());
        String imageFileName = "JPEG_" + timeStamp + "_";
        File storageDir = getExternalFilesDir(null);
        return File.createTempFile(imageFileName, ".jpg", storageDir);
    }
}
