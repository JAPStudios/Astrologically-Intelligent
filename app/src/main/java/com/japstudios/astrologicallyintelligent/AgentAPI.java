package com.japstudios.astrologicallyintelligent;

import org.json.JSONArray;
import org.json.JSONObject;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URI;
import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;

final class AgentAPI {
    private final String baseUrl;
    private final String bearerToken;

    AgentAPI(String baseUrl, String bearerToken) {
        this.baseUrl = baseUrl.replaceAll("/+$", "");
        this.bearerToken = bearerToken;
    }

    JSONArray getHistory(String sessionId) throws Exception {
        if (sessionId == null || !sessionId.matches("[A-Za-z0-9_-]{1,128}")) {
            throw new IllegalArgumentException("Invalid session ID.");
        }
        final URI endpoint;
        try {
            endpoint = new URI(baseUrl);
        } catch (java.net.URISyntaxException invalidUrl) {
            throw new IllegalArgumentException("Enter a valid HTTP or HTTPS server URL without credentials or query parameters.", invalidUrl);
        }
        String scheme = endpoint.getScheme();
        if (!("https".equalsIgnoreCase(scheme) || "http".equalsIgnoreCase(scheme))
                || endpoint.getHost() == null
                || endpoint.getUserInfo() != null
                || endpoint.getQuery() != null
                || endpoint.getFragment() != null) {
            throw new IllegalArgumentException("Enter a valid HTTP or HTTPS server URL without credentials or query parameters.");
        }

        HttpURLConnection connection = (HttpURLConnection)
                new URL(baseUrl + "/v1/sessions/" + sessionId).openConnection();
        try {
            connection.setRequestMethod("GET");
            connection.setConnectTimeout(10000);
            connection.setReadTimeout(30000);
            connection.setRequestProperty("Accept", "application/json");
            if (!bearerToken.isEmpty()) {
                connection.setRequestProperty("Authorization", "Bearer " + bearerToken);
            }
            int status = connection.getResponseCode();
            InputStream stream = status >= 400
                    ? connection.getErrorStream()
                    : connection.getInputStream();
            if (stream == null) {
                if (status == HttpURLConnection.HTTP_UNAUTHORIZED) {
                    throw new IllegalStateException("Authentication failed (HTTP 401). Check the bearer token.");
                }
                throw new IllegalStateException("Server returned HTTP " + status + " without a response body.");
            }
            String responseText;
            try (InputStream input = stream;
                 ByteArrayOutputStream output = new ByteArrayOutputStream()) {
                byte[] buffer = new byte[8192];
                int count;
                while ((count = input.read(buffer)) != -1) {
                    if (output.size() + count > 1_000_000) {
                        throw new IllegalStateException("Server response exceeded the 1 MB limit.");
                    }
                    output.write(buffer, 0, count);
                }
                responseText = output.toString(StandardCharsets.UTF_8.name());
            }
            JSONObject json;
            try {
                json = new JSONObject(responseText);
            } catch (Exception invalidJson) {
                throw new IllegalStateException("Server returned an invalid response (HTTP " + status + ").");
            }
            if (status < 200 || status >= 300) {
                throw new IllegalStateException(json.optString("error", json.optString("detail", "HTTP " + status)));
            }
            JSONArray messages = json.optJSONArray("messages");
            if (messages == null) {
                throw new IllegalStateException("Server response did not contain conversation history.");
            }
            return messages;
        } finally {
            connection.disconnect();
        }
    }

    String sendMessage(String message, String sessionId) throws Exception {
        final URI endpoint;
        try {
            endpoint = new URI(baseUrl);
        } catch (java.net.URISyntaxException invalidUrl) {
            throw new IllegalArgumentException("Enter a valid HTTP or HTTPS server URL without credentials or query parameters.", invalidUrl);
        }
        String scheme = endpoint.getScheme();
        if (!("https".equalsIgnoreCase(scheme) || "http".equalsIgnoreCase(scheme))
                || endpoint.getHost() == null
                || endpoint.getUserInfo() != null
                || endpoint.getQuery() != null
                || endpoint.getFragment() != null) {
            throw new IllegalArgumentException("Enter a valid HTTP or HTTPS server URL without credentials or query parameters.");
        }

        HttpURLConnection connection = (HttpURLConnection)
                new URL(baseUrl + "/v1/chat").openConnection();
        try {
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
            InputStream stream = status >= 400
                    ? connection.getErrorStream()
                    : connection.getInputStream();
            if (stream == null) {
                if (status == HttpURLConnection.HTTP_UNAUTHORIZED) {
                    throw new IllegalStateException("Authentication failed (HTTP 401). Check the bearer token.");
                }
                throw new IllegalStateException("Server returned HTTP " + status + " without a response body.");
            }
            String responseText = "";
            if (stream != null) {
                try (InputStream input = stream;
                     ByteArrayOutputStream output = new ByteArrayOutputStream()) {
                    byte[] buffer = new byte[8192];
                    int count;
                    while ((count = input.read(buffer)) != -1) {
                        if (output.size() + count > 1_000_000) {
                            throw new IllegalStateException("Server response exceeded the 1 MB limit.");
                        }
                        output.write(buffer, 0, count);
                    }
                    responseText = output.toString(StandardCharsets.UTF_8.name());
                }
            }
            JSONObject json;
            try {
                json = new JSONObject(responseText);
            } catch (Exception invalidJson) {
                throw new IllegalStateException("Server returned an invalid response (HTTP " + status + ").");
            }
            if (status < 200 || status >= 300) {
                throw new IllegalStateException(json.optString("error", json.optString("detail", "HTTP " + status)));
            }
            return json.getString("response");
        } finally {
            connection.disconnect();
        }
    }
}
