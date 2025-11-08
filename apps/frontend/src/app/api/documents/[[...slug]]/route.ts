import type { NextRequest } from 'next/server';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
export const revalidate = 0;

const ALLOWED_METHODS = new Set(['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']);

const sanitizeBase = (value: string | undefined): string | null => {
  if (!value || value.trim().length === 0) {
    return null;
  }
  const trimmed = value.trim();
  return trimmed.endsWith('/') ? trimmed.slice(0, -1) : trimmed;
};

const ingestionBase = () =>
  sanitizeBase(process.env.INGESTION_URL ?? process.env.NEXT_PUBLIC_INGESTION_SERVICE_URL ?? '');

const buildTargetUrl = (request: NextRequest, slug: string[] = []): string | null => {
  const base = ingestionBase();
  if (!base) {
    return null;
  }

  const suffix = slug.length ? `/${slug.join('/')}` : '';
  const search = request.nextUrl.search ?? '';
  return `${base}/api/documents${suffix}${search}`;
};

const sanitizeHeaders = (request: NextRequest): Headers => {
  const headers = new Headers();
  request.headers.forEach((value, key) => {
    const lower = key.toLowerCase();
    if (lower === 'host' || lower === 'content-length') {
      return;
    }
    headers.set(key, value);
  });
  return headers;
};

const forward = async (request: NextRequest, slug: string[] = []) => {
  const method = request.method?.toUpperCase() ?? 'GET';
  if (!ALLOWED_METHODS.has(method)) {
    return new Response(
      JSON.stringify({ error: 'Method not allowed' }),
      {
        status: 405,
        headers: { Allow: Array.from(ALLOWED_METHODS).join(', '), 'Content-Type': 'application/json' },
      },
    );
  }

  const targetUrl = buildTargetUrl(request, slug);
  if (!targetUrl) {
    return new Response(
      JSON.stringify({ error: 'Ingestion service URL not configured' }),
      { status: 502, headers: { 'Content-Type': 'application/json' } },
    );
  }

  console.log('[documents-proxy] forwarding request', { method, slug, targetUrl });

  const init: RequestInit = {
    method,
    headers: sanitizeHeaders(request),
    redirect: 'manual',
  };

  if (method !== 'GET' && method !== 'HEAD') {
    const body = await request.arrayBuffer();
    if (body.byteLength > 0) {
      init.body = body;
    }
  }

  try {
    const response = await fetch(targetUrl, init);
    const responseHeaders = new Headers();
    response.headers.forEach((value, key) => {
      if (key.toLowerCase() === 'transfer-encoding') {
        return;
      }
      responseHeaders.set(key, value);
    });

    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
    });
  } catch (error) {
    console.error('[documents-proxy] fetch failed', { targetUrl, message: (error as Error).message });
    return new Response(
      JSON.stringify({
        error: 'Failed to reach ingestion service',
        details: (error as Error).message,
      }),
      { status: 502, headers: { 'Content-Type': 'application/json' } },
    );
  }
};

export async function GET(request: NextRequest, context: { params: { slug?: string[] } }) {
  return forward(request, context.params.slug ?? []);
}

export async function POST(request: NextRequest, context: { params: { slug?: string[] } }) {
  return forward(request, context.params.slug ?? []);
}

export async function PUT(request: NextRequest, context: { params: { slug?: string[] } }) {
  return forward(request, context.params.slug ?? []);
}

export async function PATCH(request: NextRequest, context: { params: { slug?: string[] } }) {
  return forward(request, context.params.slug ?? []);
}

export async function DELETE(request: NextRequest, context: { params: { slug?: string[] } }) {
  return forward(request, context.params.slug ?? []);
}

export async function OPTIONS(request: NextRequest, context: { params: { slug?: string[] } }) {
  return forward(request, context.params.slug ?? []);
}
