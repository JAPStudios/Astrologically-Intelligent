# Astrologically Intelligent

An Android client and Python agent runtime for astrology-focused conversations.

## Python agent runtime

See [AGENT_RUNTIME.md](AGENT_RUNTIME.md) for provider configuration, API usage, persistence, tool calling, and local service security.

## Android application

The Android app is in `app/`. It provides a native chat interface to the Python runtime. Configure the server URL and, when enabled, its bearer token in the app. The Android emulator's default URL `http://10.0.2.2:8765` routes to a Python server running on the development host. Use HTTPS for remote deployments; cleartext traffic is enabled in this initial development build.

Build with Gradle 8.9, JDK 17, and Android SDK platform 35:

```sh
gradle assembleDebug
```

## Tests

```sh
python -m unittest discover -s tests -v
```
