package com.japstudios.astrologicallyintelligent;

import android.app.Activity;
import android.app.AlertDialog;
import android.os.Bundle;
import android.graphics.Typeface;
import android.view.inputmethod.InputMethodManager;
import android.content.Context;
import android.content.SharedPreferences;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class MainActivity extends Activity {
    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private SharedPreferences preferences;
    private EditText endpoint;
    private EditText token;
    private EditText prompt;
    private TextView transcript;
    private Button send;
    private String sessionId;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        preferences = getSharedPreferences("agent", MODE_PRIVATE);
        sessionId = preferences.getString("session_id", UUID.randomUUID().toString());
        preferences.edit().putString("session_id", sessionId).apply();
        buildInterface();
        loadHistory();
    }

    private void buildInterface() {
        int pad = (int) (16 * getResources().getDisplayMetrics().density);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(pad, pad, pad, pad);

        TextView title = new TextView(this);
        title.setText("Astrologically Intelligent");
        title.setTextSize(24);
        title.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        root.addView(title);

        endpoint = new EditText(this);
        endpoint.setSingleLine(true);
        endpoint.setHint("Agent server URL (e.g. https://your-server)");
        endpoint.setText(preferences.getString("endpoint", "http://10.0.2.2:8765"));
        root.addView(endpoint);

        token = new EditText(this);
        token.setSingleLine(true);
        token.setHint("Server access token (optional for local loopback)");
        token.setInputType(129);
        root.addView(token);

        LinearLayout conversationActions = new LinearLayout(this);
        conversationActions.setOrientation(LinearLayout.HORIZONTAL);
        Button conversations = new Button(this);
        conversations.setText("Conversations");
        conversations.setOnClickListener(v -> showConversations());
        conversationActions.addView(conversations, new LinearLayout.LayoutParams(0,
                LinearLayout.LayoutParams.WRAP_CONTENT, 1));
        Button newConversation = new Button(this);
        newConversation.setText("New");
        newConversation.setOnClickListener(v -> startNewConversation());
        conversationActions.addView(newConversation, new LinearLayout.LayoutParams(0,
                LinearLayout.LayoutParams.WRAP_CONTENT, 1));
        root.addView(conversationActions);

        ScrollView scroll = new ScrollView(this);
        transcript = new TextView(this);
        transcript.setTextSize(16);
        transcript.setText("Connect to the Python agent runtime to begin.\n");
        transcript.setPadding(0, pad, 0, pad);
        scroll.addView(transcript);
        root.addView(scroll, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 0, 1));

        prompt = new EditText(this);
        prompt.setHint("Ask Astrologically Intelligent");
        prompt.setMinLines(2);
        prompt.setMaxLines(5);
        root.addView(prompt);

        send = new Button(this);
        send.setText("Send");
        send.setOnClickListener(v -> submit());
        root.addView(send);
        setContentView(root);
    }

    private void startNewConversation() {
        sessionId = UUID.randomUUID().toString();
        preferences.edit().putString("session_id", sessionId).apply();
        transcript.setText("New conversation.\n");
        prompt.setText("");
    }

    private void showConversations() {
        String url = endpoint.getText().toString().trim();
        String accessToken = token.getText().toString().trim();
        executor.execute(() -> {
            try {
                org.json.JSONArray sessions = new org.json.JSONArray(
                        new AgentAPI(url, accessToken).fetchSessions());
                List<String> labels = new ArrayList<>();
                List<String> ids = new ArrayList<>();
                for (int i = 0; i < sessions.length(); i++) {
                    org.json.JSONObject item = sessions.optJSONObject(i);
                    if (item == null) continue;
                    String id = item.optString("session_id", "");
                    if (id.isEmpty()) continue;
                    String preview = item.optString("preview", "").replace('\n', ' ');
                    if (preview.length() > 72) preview = preview.substring(0, 72) + "…";
                    labels.add((id.equals(sessionId) ? "Current · " : "")
                            + preview + " (" + item.optInt("message_count") + ")");
                    ids.add(id);
                }
                runOnUiThread(() -> {
                    if (labels.isEmpty()) {
                        transcript.append("\nNo saved conversations were found.\n");
                        return;
                    }
                    new AlertDialog.Builder(this)
                            .setTitle("Conversations")
                            .setItems(labels.toArray(new String[0]), (dialog, which) -> {
                                sessionId = ids.get(which);
                                preferences.edit().putString("session_id", sessionId).apply();
                                loadHistory();
                            })
                            .setNegativeButton("Cancel", null)
                            .show();
                });
            } catch (Exception error) {
                runOnUiThread(() -> transcript.append("\nConversations unavailable: "
                        + error.getMessage() + "\n"));
            }
        });
    }

    private void loadHistory() {
        String requestedSessionId = sessionId;
        String url = endpoint.getText().toString().trim();
        String accessToken = token.getText().toString().trim();
        executor.execute(() -> {
            try {
                String history = new AgentAPI(url, accessToken).fetchHistory(requestedSessionId);
                org.json.JSONArray messages = new org.json.JSONArray(history);
                runOnUiThread(() -> {
                    if (!requestedSessionId.equals(sessionId)) return;
                    transcript.setText("");
                    if (messages.length() == 0) {
                        transcript.setText("Connect to the Python agent runtime to begin.\n");
                        return;
                    }
                    for (int i = 0; i < messages.length(); i++) {
                        org.json.JSONObject item = messages.optJSONObject(i);
                        if (item == null) continue;
                        String role = item.optString("role", "assistant");
                        String label = role.equals("user") ? "You" : "Assistant";
                        transcript.append(label + ": " + item.optString("content", "") + "\n");
                    }
                });
            } catch (Exception error) {
                runOnUiThread(() -> {
                    if (requestedSessionId.equals(sessionId)) {
                        transcript.append("History unavailable: " + error.getMessage() + "\n");
                    }
                });
            }
        });
    }

    private void submit() {
        String message = prompt.getText().toString().trim();
        String url = endpoint.getText().toString().trim();
        String accessToken = token.getText().toString().trim();
        if (message.isEmpty() || url.isEmpty()) return;

        preferences.edit().putString("endpoint", url).apply();
        prompt.setText("");
        transcript.append("\nYou: " + message + "\n");
        send.setEnabled(false);
        String requestSessionId = sessionId;
        executor.execute(() -> {
            try {
                String answer = new AgentAPI(url, accessToken).sendMessage(message, requestSessionId);
                runOnUiThread(() -> {
                    if (requestSessionId.equals(sessionId)) {
                        transcript.append("\nAssistant: " + answer + "\n");
                    }
                });
            } catch (Exception error) {
                runOnUiThread(() -> {
                    if (requestSessionId.equals(sessionId)) {
                        transcript.append("\nConnection error: " + error.getMessage() + "\n");
                    }
                });
            } finally {
                runOnUiThread(() -> send.setEnabled(true));
            }
        });
        ((InputMethodManager) getSystemService(Context.INPUT_METHOD_SERVICE))
                .hideSoftInputFromWindow(prompt.getWindowToken(), 0);
    }

    @Override
    protected void onDestroy() {
        executor.shutdownNow();
        super.onDestroy();
    }
}
