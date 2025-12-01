import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8000';

export async function POST(req: NextRequest) {
  try {
    // Forward multipart/form-data or other bodies transparently
    const contentType = req.headers.get('content-type') || '';
    const buffer = await req.arrayBuffer();

    const res = await fetch(`${BACKEND_URL}/api/upload`, {
      method: 'POST',
      headers: { 'content-type': contentType },
      body: buffer,
    });

    // If backend returns JSON
    const text = await res.text();
    try {
      const data = JSON.parse(text);
      return NextResponse.json(data, { status: res.status });
    } catch (_e) {
      // not JSON, return as text
      return new NextResponse(text, { status: res.status });
    }
  } catch (err) {
    console.error('Proxy error /api/upload:', err);
    return NextResponse.json({ error: 'Failed to reach backend' }, { status: 500 });
  }
}
