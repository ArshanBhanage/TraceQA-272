import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8000';

export const dynamic = 'force-dynamic';
export const fetchCache = 'force-no-store';

export async function GET(req: NextRequest) {
  try {
    // Get jobId from the pathname
    const parts = req.nextUrl.pathname.split('/');
    const jobId = parts[parts.length - 1];

    const res = await fetch(`${BACKEND_URL}/api/processing-status/${encodeURIComponent(jobId)}`, {
  cache: 'no-store',
});
    const data = await res.json();
    return NextResponse.json(data, {
      status: res.status,
      headers: {
        'Cache-Control': 'no-store',
      },
    });
  } catch (err) {
    console.error('Proxy error /api/processing-status/:jobId:', err);
    return NextResponse.json({ error: 'Failed to reach backend' }, { status: 500 });
  }
}
