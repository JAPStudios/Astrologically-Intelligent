package com.japstudios.astrologicallyintelligent;

import org.json.JSONObject;
import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

final class GeminiAPI {
    private final String baseUrl;
    private final String bearerToken;

    GeminiAPI(String baseUrl, String bearerToken) {
        this.baseUrl = baseUrl.replaceAll("/+$", "");
        this.bearerToken = bearerToken;
    }

    String sendMessage(String message, String sessionId) throws Exception {
        HttpURLConnection connection = (HttpURLConnection)
                new URL(baseUrl + "/v1/chat").openConnection();
        connection.setRequestMethod("POST");
        connection.setConnectTimeout(10000);
        connection.setReadTimeout(120000);
        connection.setDoOutput(true);
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
        StringBuilder response = new StringBuilder();
        try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(stream, StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) response.append(line);
        } finally {
            connection.disconnect();
        }
        JSONObject json = new JSONObject(response.toString());
        if (status < 200 || status >= 300) {
            throw new IllegalStateException(json.optString("error", "HTTP " + status));
        }
        return json.getString("response");
    }
}
