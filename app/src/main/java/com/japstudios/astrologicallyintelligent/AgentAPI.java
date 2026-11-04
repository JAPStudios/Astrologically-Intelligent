package com.japstudios.astrologicallyintelligent;

import org.json.JSONObject;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URI;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.Locale;

final class AgentAPI {
    private static final int MAX_RESPONSE_BYTES = 1_000_000;
    private final String baseUrl;
    private final String bearerToken;

    AgentAPI(String baseUrl, String bearerToken) {
        this.baseUrl = validateBaseUrl(baseUrl).replaceAll("/+$", "");
        this.bearerToken = bearerToken == null ? "" : bearerToken;
    }

    static String validateBaseUrl(String value) {
        if (value == null || value.trim().isEmpty()) {
            throw new IllegalArgumentException("Agent server URL is required");
        }
        final URI uri;
        try {
            uri = URI.create(value.trim());
        } catch (IllegalArgumentException error) {
            throw new IllegalArgumentException("Agent server URL is invalid", error);
        }
        String scheme = uri.getScheme() == null ? "" : uri.getScheme().toLowerCase(Locale.ROOT);
        String host = uri.getHost() == null ? "" : uri.getHost().toLowerCase(Locale.ROOT);
        if (!(scheme.equals("https") || scheme.equals("http"))) {
            throw new IllegalArgumentException("Agent server URL must use HTTPS (HTTP is allowed only for local development)");
        }
        if (host.isEmpty() || uri.getRawUserInfo() != null || uri.getRawQuery() != null || uri.getRawFragment() != null) {
            throw new IllegalArgumentException("Agent server URL must contain a host and must not contain credentials, a query, or a fragment");
        }
        if (uri.getPort() > 65535 || uri.getPort() == 0) {
            throw new IllegalArgumentException("Agent server URL contains an invalid port");
        }
        boolean localHost = host.equals("10.0.2.2") || host.equals("localhost")
                || host.equals("127.0.0.1") || host.equals("::1") || host.equals("[::1]");
        if (scheme.equals("http") && !localHost) {
            throw new IllegalArgumentException("Remote agent servers must use HTTPS");
        }
        return value.trim();
    }

    String fetchHistory(String sessionId) throws Exception {
        String encodedSession = java.net.URLEncoder.encode(sessionId, "UTF-8");
        HttpURLConnection connection = (HttpURLConnection)
                new URL(baseUrl + "/v1/history?session_id=" + encodedSession + "&limit=40").openConnection();
        connection.setInstanceFollowRedirects(false);
        connection.setRequestMethod("GET");
        connection.setConnectTimeout(10000);
        connection.setReadTimeout(20000);
        connection.setRequestProperty("Accept", "application/json");
        if (!bearerToken.isEmpty()) {
            connection.setRequestProperty("Authorization", "Bearer " + bearerToken);
        }
        int status = connection.getResponseCode();
        InputStream stream = status >= 200 && status < 300
                ? connection.getInputStream() : connection.getErrorStream();
        try {
            if (stream == null) throw new IllegalStateException("Agent server returned HTTP " + status);
            byte[] responseBytes;
            try (InputStream input = stream; ByteArrayOutputStream output = new ByteArrayOutputStream()) {
                byte[] buffer = new byte[8192];
                int count;
                while ((count = input.read(buffer)) != -1) {
                    if (output.size() + count > MAX_RESPONSE_BYTES) {
                        throw new IllegalStateException("Agent server response exceeded 1 MB");
                    }
                    output.write(buffer, 0, count);
                }
                responseBytes = output.toByteArray();
            }
            String response = new String(responseBytes, StandardCharsets.UTF_8);
            if (status < 200 || status >= 300) {
                try {
                    JSONObject error = new JSONObject(response);
                    throw new IllegalStateException(error.optString("error", "HTTP " + status));
                } catch (org.json.JSONException invalidJson) {
                    throw new IllegalStateException("Agent server returned HTTP " + status);
                }
            }
            return new JSONObject(response).getJSONArray("messages").toString();
        } finally {
            connection.disconnect();
        }
    }

    String sendMessage(String message, String sessionId) throws Exception {
        HttpURLConnection connection = (HttpURLConnection)
                new URL(baseUrl + "/v1/chat").openConnection();
        connection.setInstanceFollowRedirects(false);
        connection.setRequestMethod("POST");
        connection.setConnectTimeout(10000);
        connection.setReadTimeout(120000);
        connection.setDoOutput(true);
        connection.setRequestProperty("Accept", "application/json");
        connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
        if (!bearerToken.isEmpty()) {
            connection.setRequestProperty("Authorization", "Bearer " + bearerToken);
        }

        JSONObject body = new JSONObject();
        body.put("message", message);
        body.put("session_id", sessionId);
        byte[] bytes = body.toString().getBytes(StandardCharsets.UTF_8);
        connection.setFixedLengthStreamingMode(bytes.length);
        try (OutputStream output = connection.getOutputStream()) {
            output.write(bytes);
        }

        int status = connection.getResponseCode();
        InputStream stream = status >= 200 && status < 300
                ? connection.getInputStream() : connection.getErrorStream();
        try {
            if (stream == null) {
                throw new IllegalStateException("Agent server returned HTTP " + status + " without a response body");
            }
            byte[] responseBytes;
            try (InputStream input = stream; ByteArrayOutputStream output = new ByteArrayOutputStream()) {
                byte[] buffer = new byte[8192];
                int count;
                while ((count = input.read(buffer)) != -1) {
                    if (output.size() + count > MAX_RESPONSE_BYTES) {
                        throw new IllegalStateException("Agent server response exceeded 1 MB");
                    }
                    output.write(buffer, 0, count);
                }
                responseBytes = output.toByteArray();
            }
            String response = new String(responseBytes, StandardCharsets.UTF_8);
            if (status < 200 || status >= 300) {
                try {
                    JSONObject error = new JSONObject(response);
                    throw new IllegalStateException(error.optString("error", "HTTP " + status));
                } catch (org.json.JSONException invalidJson) {
                    throw new IllegalStateException("Agent server returned HTTP " + status);
                }
            }
            JSONObject json = new JSONObject(response);
            return json.getString("response");
        } finally {
            connection.disconnect();
        }
    }
}
