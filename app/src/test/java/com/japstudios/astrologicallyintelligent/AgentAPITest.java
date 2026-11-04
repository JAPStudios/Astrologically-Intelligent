package com.japstudios.astrologicallyintelligent;

import org.junit.Test;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.fail;

public final class AgentAPITest {
    @Test
    public void acceptsHttpsRemoteEndpoints() {
        assertEquals("https://agent.example.com", AgentAPI.validateBaseUrl("https://agent.example.com"));
    }

    @Test
    public void acceptsEmulatorBridgeHttpEndpoint() {
        assertEquals("http://10.0.2.2:8765", AgentAPI.validateBaseUrl("http://10.0.2.2:8765"));
    }

    @Test
    public void rejectsCleartextRemoteEndpoints() {
        assertInvalid("http://agent.example.com");
    }

    @Test
    public void rejectsCredentialsAndUrlParameters() {
        assertInvalid("https://user:secret@agent.example.com");
        assertInvalid("https://agent.example.com?token=secret");
        assertInvalid("https://agent.example.com#fragment");
    }

    @Test
    public void rejectsUnsupportedSchemesAndMissingHosts() {
        assertInvalid("ftp://agent.example.com");
        assertInvalid("https:///missing-host");
    }

    private static void assertInvalid(String value) {
        try {
            AgentAPI.validateBaseUrl(value);
            fail("Expected invalid endpoint to be rejected: " + value);
        } catch (IllegalArgumentException expected) {
            // Expected validation failure.
        }
    }
}
