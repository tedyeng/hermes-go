# Hermes Go Web Dashboard

A premium, interactive web interface dashboard for the `hermes-go` project. It consolidates all CLI transport utilities into a unified, dark-mode single-page application (SPA).

---

## 🚀 Key Features

*   **🚲 YouBike 2.0 Station Availability**: View nearby stations on the map with status colors (green/orange/red) based on real-time available bikes, capacity, and service status.
*   **🚌 Taiwan Bus ETA & Routing**: 
    *   Find nearby bus stops with real-time ETA countdowns.
    *   Plan direct bus routes to destinations, displaying stop count and ETAs.
*   **🗺️ Google Places Sights & Dining**: Query nearby restaurants, cafes, bars, and tourist spots, filtering them with dynamic chips.
*   **🚄 Japan Train Status & Route Search**:
    *   Monitor regional railway operations and warning delays.
    *   Plan travel itineraries across Japan rail stations with fare, duration, and transit directions.
*   **🗺️ Interactive Leaflet Map**: Click anywhere to pan and sync the active coordinate center, or click custom data markers to open details popups.

---

## 🛠️ Technology Stack

*   **Core**: React 19 + TypeScript + Vite
*   **Styling**: Premium custom Vanilla CSS (deep blues dark mode, glassmorphic card overlays, hover animations)
*   **Map System**: Leaflet.js (using custom pins and dark-themed OpenStreetMap tiles)
*   **Testing Frameworks**: Jest + React Testing Library (Unit) and Playwright (E2E)

---

## 📦 Available Scripts

Run the following commands inside the `frontend/` directory:

### 1. Development & Build
*   `npm run dev`: Start the Vite local development server.
*   `npm run build`: Compile TypeScript and build production assets under `dist/`.
*   `npm run preview`: Preview the production build locally.

### 2. Automated Tests
*   `npm run test`: Run Jest unit tests.
*   `npm run coverage`: Run Jest unit tests and display the branch coverage report.
*   `npm run test:e2e`: Execute Playwright end-to-end integration tests (will spin up the dev server automatically).
*   `npm run test:visual`: Run Playwright visual layout regression tests.
*   `npm run test:visual:update`: Generate or update visual reference baseline snapshots.

---

## 🧪 Testing Coverage

The project enforces high test standards. The frontend testing suite has achieved:
*   **Overall Branch Coverage**: **98.7%**
*   **Component Branch Coverage**:
    *   `MapContainer.tsx` (Leaflet Map): **100%**
    *   `Sidebar.tsx` (Interactive lists & chips): **100%**
    *   `helpers.ts` (Haversine & ETA formatters): **100%**
    *   `App.tsx` (State synchronization): **94.36%**

---

## 🚀 Running the Project Locally

1.  **Build the client assets**:
    ```bash
    cd frontend && npm run build
    ```
2.  **Start the Python FastAPI backend server**:
    Make sure you have installed the project requirements, then run:
    ```bash
    cd ..
    uv run python src/server.py
    ```
3.  Open [http://localhost:8000](http://localhost:8000) in your web browser.
