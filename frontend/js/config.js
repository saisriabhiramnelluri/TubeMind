/**
 * Frontend Configuration
 *
 * For LOCAL development: API calls go to same origin (FastAPI serves both
 * the frontend and the /api routes on localhost:8000).
 *
 * For PRODUCTION (Vercel + Hugging Face Spaces):
 * The `vercel.json` proxies all `/api/*` requests to the HF Space backend.
 * This completely bypasses CORS issues — the browser only ever talks to
 * the same Vercel origin.
 *
 * To update the backend URL, change the `destination` in vercel.json.
 */

// Uncomment and set this ONLY if you want to call the HF backend directly
// (bypassing the Vercel proxy). Not recommended due to CORS.
// window.__API_BASE__ = 'https://abhiramnell-tubemindbackend.hf.space/api';
