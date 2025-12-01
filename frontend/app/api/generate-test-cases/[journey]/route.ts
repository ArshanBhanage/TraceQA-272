import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8000';

export const dynamic = 'force-dynamic';
export const fetchCache = 'force-no-store';

export async function POST(req: NextRequest) {
  try {
    const { journey } = req.nextUrl.pathname.match(/generate-test-cases\/(.*)$/)?.groups || {};
    const parts = req.nextUrl.pathname.split('/');
    const journeyName = parts[parts.length - 1];

    const res = await fetch(`${BACKEND_URL}/api/generate-test-cases/${encodeURIComponent(journeyName)}`, {
        cache: 'no-store',
      method: 'POST'
    });

    const data = await res.json();
    return NextResponse.json(data, {
      status: res.status,
      headers: {
        'Cache-Control': 'no-store',
      },
    });
  } catch (err) {
    console.error('Proxy error /api/generate-test-cases/:journey:', err);
    return NextResponse.json({ error: 'Failed to reach backend' }, { status: 500 });
  }
}
