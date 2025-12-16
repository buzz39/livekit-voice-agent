# Agent Dashboard Frontend

This directory contains the frontend application for the Agent Dashboard, a real-time interface for monitoring agent activity, call statistics, and managing outbound calls.

## Overview

The frontend is a Single Page Application (SPA) built with React and Vite. It provides a modern, responsive user interface styled with Tailwind CSS. It communicates with the Python backend to fetch live data and trigger actions.

### Key Features

*   **Dashboard Layout**: A clean, responsive layout with a sidebar and main content area.
*   **Real-time Statistics**: Displays key metrics such as total calls, active calls, average duration, and success rates.
*   **Recent Activity**: Shows a list of recent calls with details like phone number, status, duration, and sentiment.
*   **Visualizations**: Uses Recharts to render charts for data visualization (e.g., call volume over time).
*   **Active Call Monitoring**: Panel to view currently active calls (placeholder for future real-time integration).

## Tech Stack

*   **Framework**: [React](https://react.dev/) (v19)
*   **Build Tool**: [Vite](https://vitejs.dev/)
*   **Styling**: [Tailwind CSS](https://tailwindcss.com/) (v3)
*   **Icons**: [Lucide React](https://lucide.dev/)
*   **Charts**: [Recharts](https://recharts.org/)
*   **Utilities**: `clsx`, `tailwind-merge` for class name management.

## Prerequisites

*   [Node.js](https://nodejs.org/) (Latest LTS recommended)
*   [npm](https://www.npmjs.com/) (comes with Node.js)

## Getting Started

1.  **Navigate to the frontend directory:**

    ```bash
    cd frontend
    ```

2.  **Install dependencies:**

    ```bash
    npm install
    ```

3.  **Start the development server:**

    ```bash
    npm run dev
    ```

    The application will be available at `http://localhost:5173`.

## Configuration

The API client is configured in `src/api.js`. Currently, it is configured to point to `https://livekit-outbound-api.tinysaas.fun` for the backend URL.

To change the backend URL, update the `API_BASE_URL` constant in `src/api.js`.

## Building for Production

To create a production build:

```bash
npm run build
```

The build artifacts will be output to the `dist` directory. You can preview the production build locally using:

```bash
npm run preview
```

## Project Structure

```
frontend/
├── public/             # Static assets
├── src/
│   ├── components/     # Reusable UI components
│   ├── api.js          # API client for backend communication
│   ├── App.jsx         # Main application component
│   ├── main.jsx        # Entry point
│   └── index.css       # Global styles and Tailwind directives
├── index.html          # HTML template
├── package.json        # Dependencies and scripts
├── tailwind.config.js  # Tailwind CSS configuration
└── vite.config.js      # Vite configuration
```

## Linting

To run the linter:

```bash
npm run lint
```
