import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8000';

export const dynamic = 'force-dynamic';
export const fetchCache = 'force-no-store';

export async function GET(req: NextRequest) {
  try {
    // Extract last path segment and decode any percent-encoding
    const parts = req.nextUrl.pathname.split('/');
    let journeyName = parts[parts.length - 1] || '';
    try {
      journeyName = decodeURIComponent(journeyName);
    } catch (e) {
      // fall back to raw value if decoding fails
    }
    console.log(`Proxying test-cases request for journey: ${journeyName} (encoded: ${encodeURIComponent(journeyName)})`);
    const res = await fetch(`${BACKEND_URL}/api/test-cases/${encodeURIComponent(journeyName)}`,{
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
    console.error('Proxy error /api/test-cases/:journey:', err);
    return NextResponse.json({ error: 'Failed to reach backend' }, { status: 500 });
  }
}
