package com.japstudios.astrologicallyintelligent;

import android.app.Activity;
import android.os.Bundle;
import android.graphics.Typeface;
import android.view.View;
import android.view.inputmethod.InputMethodManager;
import android.content.Context;
import android.content.SharedPreferences;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import org.json.JSONArray;
import org.json.JSONObject;
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
    private Button historyButton;
    private ScrollView scroll;
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
        endpoint.setText(preferences.getString("endpoint", "http://10.0.2.2:7000"));
        root.addView(endpoint);

        token = new EditText(this);
        token.setSingleLine(true);
        token.setHint("Admin chat API token, or ASTRO_AI_API_TOKEN when auth is disabled");
        token.setInputType(129);
        root.addView(token);

        historyButton = new Button(this);
        historyButton.setText("Load saved conversation");
        historyButton.setOnClickListener(v -> loadHistory());
        root.addView(historyButton);

        scroll = new ScrollView(this);
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

    private void loadHistory() {
        String url = endpoint.getText().toString().trim();
        String accessToken = token.getText().toString().trim();
        if (url.isEmpty()) return;
        preferences.edit().putString("endpoint", url).apply();
        historyButton.setEnabled(false);
        send.setEnabled(false);
        executor.execute(() -> {
            try {
                JSONArray messages = new AgentAPI(url, accessToken).getHistory(sessionId);
                runOnUiThread(() -> {
                    transcript.setText("");
                    if (messages.length() == 0) {
                        transcript.setText("No saved conversation yet. Send a message to begin.\n");
                    } else {
                        for (int i = 0; i < messages.length(); i++) {
                            JSONObject message = messages.optJSONObject(i);
                            if (message == null) continue;
                            String role = message.optString("role", "assistant");
                            String content = message.optString("content", "");
                            if (content.isEmpty()) continue;
                            String label = "user".equals(role) ? "You" : "Astrologically Intelligent";
                            transcript.append(label + ": " + content + "\n\n");
                        }
                    }
                    scroll.post(() -> scroll.fullScroll(View.FOCUS_DOWN));
                });
            } catch (Exception error) {
                runOnUiThread(() -> transcript.setText(
                        "Could not load saved conversation. Check the server URL and access token, then select Load saved conversation again.\n"
                ));
            } finally {
                runOnUiThread(() -> {
                    historyButton.setEnabled(true);
                    send.setEnabled(true);
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
        executor.execute(() -> {
            try {
                String answer = new AgentAPI(url, accessToken).sendMessage(message, sessionId);
                runOnUiThread(() -> transcript.append("\nAstrologically Intelligent: " + answer + "\n"));
            } catch (Exception error) {
                runOnUiThread(() -> transcript.append("\nConnection error: "
                        + error.getMessage() + "\n"));
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
