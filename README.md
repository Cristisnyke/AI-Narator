# AI-Narator

AI-Narator primarily for video-games powered via ChatGPT API

## Screen Coach Overlay

The `screen_coach` package provides a lightweight overlay that captures your screen, sends frames to the OpenAI vision API, and displays concise coaching feedback.

### Prerequisites

* Python 3.10 or newer
* An OpenAI API key with access to a vision-capable model (e.g. `gpt-4o-mini`)
* Desktop environment capable of running PySide6 overlays

### Setup

1. **Clone the repository** and move into the project directory.

   ```bash
   git clone <repo-url>
   cd AI-Narator
   ```

2. **Create and activate a virtual environment** (recommended).

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use: .venv\\Scripts\\activate
   ```

3. **Install dependencies**.

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**.

   Create a `.env` file in the project root containing at minimum:

   ```env
   OPENAI_API_KEY=sk-...
   ```

   Optional variables:

   * `SCREEN_COACH_MODEL` – override the default model (`gpt-4o-mini`).
   * `SCREEN_COACH_INTERVAL` – polling interval in seconds (default `2`).
   * `SCREEN_COACH_WINDOW_KEYWORDS` – comma-separated keywords; only analyze when the active window title matches.
   * `SCREEN_COACH_REDACT` – redaction regions defined as `left,top,right,bottom` separated by semicolons.
   * `SCREEN_COACH_PROMPT` – custom coaching instructions.
   * `SCREEN_COACH_MAX_TOKENS` – maximum tokens returned by the model (default `200`).

### Running Screen Coach

After completing the setup steps:

```bash
python -m screen_coach.main
```

Command-line options let you override the same configuration values without editing environment variables. Use `python -m screen_coach.main --help` for details.

The overlay will appear near the top-right corner of your display. It captures frames at the configured interval, applies optional redaction, and updates its guidance only when the screen meaningfully changes.
