# SpeakAI – Real-Time Communication Coach

An AI-powered speaking coach that joins your video call as an interactive participant, providing **real-time feedback** on filler words, pace, confidence, hedging language, and body language.

## Architecture

```
┌─────────────────────────────────┐
│  Next.js Frontend (React 19)    │
│  ● Stream Video call panel      │
│  ● Real-time coaching dashboard │
│  ● WebSocket metrics stream     │
└──────────┬──────────────────────┘
           │ ws://localhost:8000/ws/metrics
┌──────────▼──────────────────────┐
│  FastAPI Backend (Python)       │
│  ● Agent lifecycle management   │
│  ● Session & analytics REST API │
│  ● WebSocket event forwarding   │
└──────────┬──────────────────────┘
           │
┌──────────▼──────────────────────┐
│  Vision Agents SDK              │
│  ● Gemini 2.5 Flash (native    │
│    audio + video, realtime)     │
│  ● GetStream Edge (WebRTC)      │
│  ● Speech & Video Processors    │
└─────────────────────────────────┘
```

**Key:** Gemini handles speech-to-text, text-to-speech, *and* video understanding natively — no separate MediaPipe/Whisper/TTS pipelines.

## Features

| Feature | Description |
|---------|-------------|
| **Filler Word Detection** | Counts "um", "uh", "like", "you know", etc. with per-window and session totals |
| **Pace Analysis** | Words-per-minute tracking with optimal range (120–160 WPM) guidance |
| **Confidence Scoring** | Composite 0–100 score from filler rate, pace, hedging, and vocabulary diversity |
| **Hedging Language** | Detects weak qualifiers ("I think maybe", "sort of", "kind of") |
| **Body Language** | Gemini-powered observations on posture, eye contact, gestures, expressions |
| **Live Coaching Feed** | Scrolling event timeline with color-coded coaching moments |
| **Session Analytics** | Historical performance tracking with trend charts |
| **Demo Mode** | Simulated metrics for testing without API keys |

## Prerequisites

- **Node.js** ≥ 18
- **Python** ≥ 3.11
- **Stream Video** account → [getstream.io](https://getstream.io)
- **Google AI** API key → [aistudio.google.com](https://aistudio.google.com)

## Quick Start

### 1. Clone & configure

```bash
cd SpeakAI
cp .env.example .env
# Fill in your API keys in .env
```

### 2. Backend

```bash
cd backend
pip install -r requirements.txt
cd ..
python -m uvicorn backend.server:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) and navigate to the **Dashboard**.

### 4. Try Demo Mode

Click **Start Demo** on the dashboard — this generates simulated coaching metrics without needing API keys or a camera.

## Project Structure

```
SpeakAI/
├── .env.example
├── README.md
├── backend/
│   ├── __init__.py
│   ├── server.py              # FastAPI server + WebSocket hub
│   ├── requirements.txt
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py          # Environment config
│   └── agent/
│       ├── __init__.py
│       ├── main.py            # Agent creation & call join
│       ├── communication_coach.md
│       ├── events/
│       │   └── coach_events.py
│       ├── processors/
│       │   ├── speech_analyzer.py
│       │   ├── video_analyzer.py
│       │   └── session_recorder.py
│       ├── post_session/
│       │   ├── report_generator.py
│       │   ├── exercise_library.py
│       │   └── progress_tracker.py
│       └── memory/
│           └── memory_manager.py
├── frontend/
│   ├── package.json
│   ├── next.config.ts
│   ├── tsconfig.json
│   ├── postcss.config.mjs
│   ├── eslint.config.mjs
│   └── src/
│       ├── app/
│       │   ├── page.tsx               # Landing page
│       │   ├── layout.tsx
│       │   ├── globals.css
│       │   └── (dashboard)/
│       │       ├── layout.tsx
│       │       ├── dashboard/page.tsx  # Main coaching dashboard
│       │       ├── analytics/page.tsx
│       │       ├── history/page.tsx
│       │       ├── practice/page.tsx
│       │       └── settings/page.tsx
│       ├── components/
│       │   ├── dashboard/
│       │   │   ├── StreamCallPanel.tsx
│       │   │   ├── ChatPanel.tsx
│       │   │   ├── CoachingFeedPanel.tsx
│       │   │   └── ConfidenceBreakdown.tsx
│       │   ├── analytics/
│       │   │   └── PerformanceChart.tsx
│       │   ├── layout/
│       │   │   ├── Sidebar.tsx
│       │   │   └── Topbar.tsx
│       │   └── ui/
│       │       ├── GlassCard.tsx
│       │       ├── AnimatedNumber.tsx
│       │       ├── Badge.tsx
│       │       ├── MetricCard.tsx
│       │       ├── PaceBadge.tsx
│       │       ├── FillerCounter.tsx
│       │       └── GradientBlobs.tsx
│       ├── hooks/
│       │   └── useMetricsStream.ts
│       └── lib/
│           ├── types.ts
│           ├── sessionStore.ts
│           └── utils.ts
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `STREAM_API_KEY` | Yes | Stream Video API key |
| `STREAM_API_SECRET` | Yes | Stream Video API secret |
| `NEXT_PUBLIC_STREAM_API_KEY` | Yes | Same Stream key, exposed to browser |
| `GOOGLE_API_KEY` | Yes | Google AI / Gemini API key |
| `GEMINI_REALTIME_MODEL` | No | Model override (default: `gemini-2.5-flash-native-audio-preview`) |
| `HOST` | No | Backend bind address (default: `0.0.0.0`) |
| `PORT` | No | Backend port (default: `8000`) |
| `CORS_ORIGINS` | No | Comma-separated allowed origins |

## Tech Stack

- **Frontend:** Next.js 16, React 19, TypeScript, Tailwind CSS v4, Framer Motion, Recharts, Stream Video React SDK
- **Backend:** Python, FastAPI, Vision Agents SDK, Gemini 2.5 Flash Realtime, GetStream Edge (WebRTC)
- **Communication:** WebSocket for real-time metric streaming, REST for analytics/history

## License

MIT
