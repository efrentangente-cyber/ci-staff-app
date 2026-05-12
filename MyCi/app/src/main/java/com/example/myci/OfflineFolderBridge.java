package com.example.myci;

import android.app.Activity;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.os.Environment;
import android.util.Base64;
import android.webkit.JavascriptInterface;
import android.widget.Toast;

import androidx.annotation.Nullable;

import java.io.File;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;

/**
 * Exposes filesystem export for offline CI packages under app-scoped storage
 * (.../Documents/CI_Offline_Packages/) so drafts are visible like a folder in Files managers.
 */
public class OfflineFolderBridge {

    private final Activity activity;

    public OfflineFolderBridge(Activity activity) {
        this.activity = activity;
    }

    /** Root directory for all queued packages under app external files (Documents). */
    public File packagesRoot() {
        File base = activity.getExternalFilesDir(Environment.DIRECTORY_DOCUMENTS);
        if (base == null) {
            base = activity.getFilesDir();
        }
        File root = new File(base, "CI_Offline_Packages");
        //noinspection ResultOfMethodCallIgnored
        root.mkdirs();
        return root;
    }

    private static String sanitizeFolder(@Nullable String name) {
        if (name == null || name.trim().isEmpty()) {
            return "package";
        }
        return name.trim().replaceAll("[^a-zA-Z0-9._\\-]", "_");
    }

    private static String sanitizeFileName(@Nullable String name, int fallbackIndex) {
        if (name == null || name.trim().isEmpty()) {
            return "evidence_" + fallbackIndex + ".jpg";
        }
        String s = name.trim().replaceAll("[\\\\/:*?\"<>|\\x00-\\x1F]", "_");
        if (s.isEmpty()) {
            return "evidence_" + fallbackIndex + ".jpg";
        }
        if (s.length() > 120) {
            s = s.substring(0, 120);
        }
        return s;
    }

    /**
     * Write package manifest JSON into {@code CI_Offline_Packages/<folder>/package.json}.
     *
     * @return absolute folder path on success, or string starting with "ERR:"
     */
    @JavascriptInterface
    public String writePackageJson(String folderName, String json) {
        try {
            File dir = new File(packagesRoot(), sanitizeFolder(folderName));
            if (!dir.exists() && !dir.mkdirs()) {
                return "ERR:mkdir_failed";
            }
            File out = new File(dir, "package.json");
            try (FileOutputStream fos = new FileOutputStream(out)) {
                fos.write(json.getBytes(StandardCharsets.UTF_8));
            }
            return dir.getAbsolutePath();
        } catch (Exception e) {
            return "ERR:" + e.getMessage();
        }
    }

    /**
     * Writes one evidence file; {@code base64DataUrlOrRaw} may be full data URL or raw base64.
     *
     * @return "OK" or string starting with "ERR:"
     */
    @JavascriptInterface
    public String writeEvidenceFile(String folderName, String fileName, String base64DataUrlOrRaw) {
        try {
            String b64 = base64DataUrlOrRaw != null ? base64DataUrlOrRaw.trim() : "";
            int idx = b64.indexOf("base64,");
            if (idx >= 0) {
                b64 = b64.substring(idx + 7);
            }
            byte[] bytes = Base64.decode(b64, Base64.DEFAULT);
            File dir = new File(packagesRoot(), sanitizeFolder(folderName));
            if (!dir.exists() && !dir.mkdirs()) {
                return "ERR:mkdir_evidence";
            }
            String fn = sanitizeFileName(fileName, 0);
            File out = new File(dir, fn);
            if (out.exists()) {
                int dot = fn.lastIndexOf('.');
                String base = dot > 0 ? fn.substring(0, dot) : fn;
                String ext = dot > 0 ? fn.substring(dot) : "";
                fn = base + "_" + System.nanoTime() + ext;
                out = new File(dir, fn);
            }
            try (FileOutputStream fos = new FileOutputStream(out)) {
                fos.write(bytes);
            }
            return "OK";
        } catch (Exception e) {
            return "ERR:" + e.getMessage();
        }
    }

    @JavascriptInterface
    public String getPackagesRootAbsolutePath() {
        return packagesRoot().getAbsolutePath();
    }

    /** Copies Documents/CI_Offline path to clipboard — user can paste in Files app or Notes. */
    @JavascriptInterface
    public void copyPackagesRootPathToClipboard() {
        activity.runOnUiThread(() -> {
            String path = packagesRoot().getAbsolutePath();
            ClipboardManager cm = (ClipboardManager) activity.getSystemService(Activity.CLIPBOARD_SERVICE);
            if (cm != null) {
                cm.setPrimaryClip(ClipData.newPlainText("CI Offline packages folder", path));
                Toast.makeText(
                        activity,
                        "Copied folder path. Open Files → Android/data → … → CI_Offline_Packages.\n\n" + path,
                        Toast.LENGTH_LONG
                ).show();
            }
        });
    }
}
