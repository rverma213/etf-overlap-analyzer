import { ETFInfo, OverlapResult } from './types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function fetchETFs(): Promise<ETFInfo[]> {
  const response = await fetch(`${API_BASE}/api/etfs`);
  if (!response.ok) {
    throw new Error('Failed to fetch ETFs');
  }
  return response.json();
}

export async function analyzeOverlap(ticker1: string, ticker2: string): Promise<OverlapResult> {
  const response = await fetch(`${API_BASE}/api/overlap`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ ticker1, ticker2 }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to analyze overlap');
  }

  return response.json();
}
