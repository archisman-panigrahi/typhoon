package io.github.archisman_panigrahi.typhoon

import android.annotation.SuppressLint
import android.content.Intent
import android.graphics.Bitmap
import android.net.Uri
import android.os.Bundle
import android.webkit.*
import androidx.activity.OnBackPressedCallback
import androidx.appcompat.app.AppCompatActivity
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout

class MainActivity : AppCompatActivity() {
    private lateinit var webView: WebView
    private lateinit var swipeRefresh: SwipeRefreshLayout

    // JS bridge to open URLs externally
    inner class JSBridge {
        @JavascriptInterface
        fun openExternal(url: String) {
            val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
            startActivity(intent)
        }
    }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        webView = findViewById(R.id.webview)
        swipeRefresh = findViewById(R.id.swipeRefresh)

        // Enable pull to refresh
        swipeRefresh.setOnRefreshListener {
            webView.reload()
        }

        with(webView.settings) {
            javaScriptEnabled = true
            domStorageEnabled = true
            cacheMode = WebSettings.LOAD_DEFAULT
            allowFileAccess = true
            allowContentAccess = true
            setSupportMultipleWindows(true)
        }

        webView.addJavascriptInterface(JSBridge(), "AndroidBridge")

        webView.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView?, request: WebResourceRequest): Boolean {
                val url = request.url.toString()
                return if (url.startsWith("file:///android_asset/")) {
                    false
                } else {
                    val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
                    startActivity(intent)
                    true
                }
            }

            override fun onPageStarted(view: WebView?, url: String?, favicon: Bitmap?) {
                swipeRefresh.isRefreshing = true
            }

            override fun onPageFinished(view: WebView?, url: String?) {
                swipeRefresh.isRefreshing = false

                // Inject JavaScript to iframe
                webView.evaluateJavascript(
                    """
                    (function() {
                        function attachClickInterceptorToIframe(iframe) {
                            try {
                                const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                                iframeDoc.addEventListener('click', function(event) {
                                    let target = event.target;
                                    while (target && target.tagName !== 'A') {
                                        target = target.parentElement;
                                    }
                                    if (target && target.tagName === 'A') {
                                        const href = target.getAttribute('href');
                                        if (href && !href.startsWith('#')) {
                                            event.preventDefault();
                                            window.AndroidBridge.openExternal(href);
                                        }
                                    }
                                }, true);
                            } catch (e) {
                                console.log("Iframe not ready or cross-origin: " + e);
                            }
                        }

                        const iframe = document.querySelector('iframe');
                        if (iframe) {
                            iframe.addEventListener('load', function() {
                                attachClickInterceptorToIframe(iframe);
                            });

                            // Handle already-loaded iframe
                            if (iframe.contentDocument && iframe.contentDocument.readyState === 'complete') {
                                attachClickInterceptorToIframe(iframe);
                            }
                        }
                    })();
                    """.trimIndent(),
                    null
                )
            }
        }

        webView.webChromeClient = WebChromeClient()

        webView.loadUrl("file:///android_asset/index.html")

        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                if (webView.canGoBack()) webView.goBack() else finish()
            }
        })
    }

    override fun onDestroy() {
        webView.destroy()
        super.onDestroy()
    }
}
