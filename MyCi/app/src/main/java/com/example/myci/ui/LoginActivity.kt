package com.example.myci.ui

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.example.myci.MyCiApp
import com.example.myci.databinding.ActivityLoginBinding
import com.example.myci.data.remote.LoginRequest
import com.example.myci.web.WebAppIntents
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import retrofit2.HttpException

class LoginActivity : AppCompatActivity() {

    private lateinit var binding: ActivityLoginBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityLoginBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // Already logged in? skip straight to the right native screen (mirrors web routing by role).
        lifecycleScope.launch {
            val token = MyCiApp.instance.tokenStore.currentToken()
            if (!token.isNullOrBlank()) {
                val role = MyCiApp.instance.tokenStore.role.first().orEmpty()
                openNativeHomeForRole(role)
            }
        }

        binding.btnLogin.setOnClickListener { attemptLogin() }
        binding.btnUseWeb.setOnClickListener {
            startActivity(WebAppIntents.createMainIntent(this, "/login", false))
            finish()
        }
    }

    private fun attemptLogin() {
        val email = binding.etEmail.text?.toString()?.trim().orEmpty()
        val pass = binding.etPassword.text?.toString().orEmpty()
        if (email.isEmpty() || pass.isEmpty()) {
            Toast.makeText(this, "Email and password required", Toast.LENGTH_SHORT).show()
            return
        }
        binding.progress.visibility = View.VISIBLE
        binding.btnLogin.isEnabled = false

        lifecycleScope.launch {
            val app = MyCiApp.instance
            try {
                val resp = withContext(Dispatchers.IO) {
                    app.api.login(LoginRequest(email, pass))
                }
                app.tokenStore.save(resp.token, resp.role, resp.name)
                openNativeHomeForRole(resp.role)
            } catch (e: HttpException) {
                val text = when (e.code()) {
                    404 -> "Cannot reach login API (404). Use the same base URL as Open Web in strings.xml and deploy the Flask mobile_api blueprint."
                    401 -> "Invalid email or password."
                    in 500..599 -> "Server error (${e.code()}). Try again later."
                    else -> "Login failed (HTTP ${e.code()})"
                }
                Toast.makeText(this@LoginActivity, text, Toast.LENGTH_LONG).show()
            } catch (e: Exception) {
                Toast.makeText(
                    this@LoginActivity,
                    "Login failed: ${e.message ?: "unknown error"}",
                    Toast.LENGTH_LONG
                ).show()
            } finally {
                binding.progress.visibility = View.GONE
                binding.btnLogin.isEnabled = true
            }
        }
    }

    /**
     * Loan staff / admin use the loan dashboard; CI staff lands on assigned cases
     * (same separation as the web app’s dashboards).
     */
    private fun openNativeHomeForRole(role: String) {
        val dest = when (role) {
            "ci_staff" -> CiCasesActivity::class.java
            else -> HomeActivity::class.java
        }
        startActivity(Intent(this, dest))
        finish()
    }
}
