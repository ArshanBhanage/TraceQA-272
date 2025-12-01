import { NextRequest, NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8000';

export async function GET(_req: NextRequest) {
  try {
    const res = await fetch(`${BACKEND_URL}/api/journeys`, {
  cache: 'no-store',
});
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err) {
    console.error('Proxy error /api/journeys:', err);
    return NextResponse.json({ error: 'Failed to reach backend' }, { status: 500 });
  }
}
