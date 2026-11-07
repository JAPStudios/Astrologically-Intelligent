package com.japstudios.astrologicallyintelligent;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import org.junit.After;
import org.junit.Test;
import org.json.JSONArray;

import java.io.ByteArrayOutputStream;
import java.io.EOFException;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.atomic.AtomicReference;

public final class AgentAPITest {
    private ServerSocket server;
    private Thread serverThread;

    @After
    public void tearDown() throws Exception {
        if (server != null) {
            server.close();
            server = null;
        }
        if (serverThread != null) {
            serverThread.join(1000);
            serverThread = null;
        }
    }

    private static String readAsciiLine(InputStream input) throws IOException {
        ByteArrayOutputStream line = new ByteArrayOutputStream();
        int previous = -1;
        int current;
        while ((current = input.read()) != -1) {
            if (previous == '\r' && current == '\n') break;
            if (previous != -1) line.write(previous);
            previous = current;
        }
        if (current == -1 && line.size() == 0 && previous == -1) return null;
        if (previous != -1 && previous != '\r') line.write(previous);
        return line.toString(StandardCharsets.US_ASCII.name());
    }

    private String startServer(int status, String response,
                               AtomicReference<String> requestBody,
                               AtomicReference<String> authorization,
                               AtomicReference<String> method) throws IOException {
        server = new ServerSocket(0, 1, InetAddress.getByName("127.0.0.1"));
        server.setSoTimeout(5000);
        ServerSocket listeningSocket = server;
        serverThread = new Thread(() -> {
            try (Socket socket = listeningSocket.accept()) {
                InputStream input = socket.getInputStream();
                OutputStream output = socket.getOutputStream();
                String requestLine = readAsciiLine(input);
                if (requestLine == null) throw new EOFException("Client closed before sending an HTTP request.");
                String[] requestParts = requestLine.split(" ", 3);
                if (method != null) method.set(requestParts[0]);
                int contentLength = 0;
                String header;
                while ((header = readAsciiLine(input)) != null && !header.isEmpty()) {
                    int separator = header.indexOf(':');
                    if (separator <= 0) continue;
                    String name = header.substring(0, separator).trim();
                    String value = header.substring(separator + 1).trim();
                    if ("Authorization".equalsIgnoreCase(name) && authorization != null) {
                        authorization.set(value);
                    } else if ("Content-Length".equalsIgnoreCase(name)) {
                        contentLength = Integer.parseInt(value);
                    }
                }
                byte[] body = new byte[contentLength];
                int offset = 0;
                while (offset < contentLength) {
                    int count = input.read(body, offset, contentLength - offset);
                    if (count < 0) throw new EOFException("Client closed before sending the complete request body.");
                    offset += count;
                }
                if (requestBody != null) requestBody.set(new String(body, StandardCharsets.UTF_8));
                byte[] responseBytes = response.getBytes(StandardCharsets.UTF_8);
                String reason = status == 401 ? "Unauthorized" : (status == 403 ? "Forbidden" : (status >= 200 && status < 300 ? "OK" : "Bad Request"));
                String headers = "HTTP/1.1 " + status + " " + reason + "\r\n"
                        + "Content-Type: application/json; charset=utf-8\r\n"
                        + "Content-Length: " + responseBytes.length + "\r\n"
                        + "Connection: close\r\n\r\n";
                output.write(headers.getBytes(StandardCharsets.US_ASCII));
                output.write(responseBytes);
                output.flush();
            } catch (IOException ignored) {
                // The oversized-response test deliberately closes the connection early.
            }
        }, "agent-api-test-server");
        serverThread.setDaemon(true);
        serverThread.start();
        return "http://127.0.0.1:" + server.getLocalPort();
    }
    @Test
    public void sendsAuthenticatedChatRequestAndReturnsResponse() throws Exception {
        AtomicReference<String> body = new AtomicReference<>();
        AtomicReference<String> auth = new AtomicReference<>();
        AtomicReference<String> method = new AtomicReference<>();
        String base = startServer(200, "{\"session_id\":\"s1\",\"response\":\"ready\"}",
                body, auth, method);

        String result = new AgentAPI(base, "test-bearer").sendMessage("hello", "s1");

        assertEquals("ready", result);
        assertEquals("POST", method.get());
        assertEquals("Bearer test-bearer", auth.get());
        assertTrue(body.get().contains("\"message\":\"hello\""));
        assertTrue(body.get().contains("\"session_id\":\"s1\""));
    }

    @Test
    public void reportsStructuredHttpErrors() throws Exception {
        String base = startServer(400, "{\"error\":\"invalid_request\"}",
                null, new AtomicReference<>(), new AtomicReference<>());
        try {
            new AgentAPI(base, "test-token").sendMessage("hello", "s1");
            fail("Expected an HTTP error");
        } catch (IllegalStateException error) {
            assertEquals("invalid_request", error.getMessage());
        }
    }

    @Test
    public void reportsApplicationAuthorizationDetails() throws Exception {
        String base = startServer(403, "{\"detail\":\"Administrator access required.\"}",
                null, new AtomicReference<>(), new AtomicReference<>());
        try {
            new AgentAPI(base, "test-token").sendMessage("hello", "s1");
            fail("Expected an authorization error");
        } catch (IllegalStateException error) {
            assertEquals("Administrator access required.", error.getMessage());
        }
    }

    @Test
    public void reportsUnauthorizedWhenHttpErrorStreamIsUnavailable() throws Exception {
        String base = startServer(401, "{\"error\":\"unauthorized\"}",
                null, new AtomicReference<>(), new AtomicReference<>());
        try {
            new AgentAPI(base, "bad-token").sendMessage("hello", "s1");
            fail("Expected an authentication error");
        } catch (IllegalStateException error) {
            assertEquals("Authentication failed (HTTP 401). Check the bearer token.", error.getMessage());
        }
    }

    @Test
    public void restoresSessionHistoryWithBearerAuthentication() throws Exception {
        AtomicReference<String> auth = new AtomicReference<>();
        AtomicReference<String> method = new AtomicReference<>();
        String base = startServer(200,
                "{\"session_id\":\"s1\",\"messages\":[{\"role\":\"user\",\"content\":\"hello\"},{\"role\":\"assistant\",\"content\":\"ready\"}]}",
                null, auth, method);

        JSONArray messages = new AgentAPI(base, "test-bearer").getHistory("s1");

        assertEquals(2, messages.length());
        assertEquals("user", messages.getJSONObject(0).getString("role"));
        assertEquals("hello", messages.getJSONObject(0).getString("content"));
        assertEquals("assistant", messages.getJSONObject(1).getString("role"));
        assertEquals("GET", method.get());
        assertEquals("Bearer test-bearer", auth.get());
    }

    @Test
    public void rejectsUnsafeHistorySessionIdsBeforeConnecting() throws Exception {
        try {
            new AgentAPI("http://127.0.0.1:1", "").getHistory("../private");
            fail("Expected an unsafe session ID to be rejected");
        } catch (IllegalArgumentException expected) {
            assertEquals("Invalid session ID.", expected.getMessage());
        }
    }

    @Test
    public void rejectsInvalidServerUrlsBeforeConnecting() throws Exception {
        for (String url : new String[] {
                "ftp://example.com",
                "https://user:password@example.com",
                "https://example.com?token=secret",
                "https://example.com/#fragment",
                "not a URL"
        }) {
            try {
                new AgentAPI(url, "").sendMessage("hello", "s1");
                fail("Expected invalid URL to be rejected: " + url);
            } catch (IllegalArgumentException expected) {
                assertFalse(expected.getMessage().isEmpty());
            }
        }
    }

    @Test
    public void rejectsOversizedServerResponses() throws Exception {
        String largeResponse = "{\"response\":\"" + "x".repeat(1_000_010) + "\"}";
        String base = startServer(200, largeResponse,
                null, new AtomicReference<>(), new AtomicReference<>());
        try {
            new AgentAPI(base, "").sendMessage("hello", "s1");
            fail("Expected oversized response to be rejected");
        } catch (IllegalStateException error) {
            assertEquals("Server response exceeded the 1 MB limit.", error.getMessage());
        }
    }
}
