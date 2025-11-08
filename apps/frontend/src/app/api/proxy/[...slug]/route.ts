import type { NextRequest } from 'next/server';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
export const revalidate = 0;

const SERVICE_MAP: Record<string, string | undefined> = {
  auth: process.env.AUTH_URL ?? process.env.NEXT_PUBLIC_AUTH_SERVICE_URL,
  citizen: process.env.CITIZEN_URL ?? process.env.NEXT_PUBLIC_CITIZEN_SERVICE_URL,
  ingestion: process.env.INGESTION_URL ?? process.env.NEXT_PUBLIC_INGESTION_SERVICE_URL,
  notification: process.env.NOTIFICATION_URL ?? process.env.NEXT_PUBLIC_NOTIFICATION_SERVICE_URL,
  signature: process.env.SIGNATURE_URL ?? process.env.NEXT_PUBLIC_SIGNATURE_SERVICE_URL,
  transfer: process.env.TRANSFER_URL ?? process.env.NEXT_PUBLIC_TRANSFER_SERVICE_URL,
  metadata: process.env.METADATA_URL ?? process.env.NEXT_PUBLIC_METADATA_SERVICE_URL,
  mintic: process.env.MINTIC_CLIENT_URL ?? process.env.NEXT_PUBLIC_MINTIC_SERVICE_URL,
};

const ALLOWED_METHODS = new Set(['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']);

const buildTargetUrl = (request: NextRequest, slug: string[]): string | null => {
  const [service, ...rest] = slug;

  if (!service) {
    return null;
  }

  const baseUrl = SERVICE_MAP[service];

  if (!baseUrl) {
    return null;
  }

  const sanitizedBase = baseUrl.endsWith('/') ? baseUrl.slice(0, -1) : baseUrl;
  const pathSuffix = rest.length ? `/${rest.join('/')}` : '';
  const search = request.nextUrl.search ?? '';

  return `${sanitizedBase}${pathSuffix}${search}`;
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

const forward = async (request: NextRequest, slug: string[]) => {
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
      JSON.stringify({ error: 'Unknown target service' }),
      { status: 502, headers: { 'Content-Type': 'application/json' } },
    );
  }

  console.log('[proxy] forwarding request', { method, slug, targetUrl });

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
    console.error('[proxy] fetch failed', { targetUrl, message: (error as Error).message });
    return new Response(
      JSON.stringify({
        error: 'Failed to reach target service',
        details: (error as Error).message,
      }),
      { status: 502, headers: { 'Content-Type': 'application/json' } },
    );
  }
};

export async function GET(request: NextRequest, context: { params: { slug?: string[] } }) {
  console.log('[proxy] GET params', context.params);
  return forward(request, context.params.slug ?? []);
}

export async function POST(request: NextRequest, context: { params: { slug?: string[] } }) {
  console.log('[proxy] POST params', context.params);
  return forward(request, context.params.slug ?? []);
}

export async function PUT(request: NextRequest, context: { params: { slug?: string[] } }) {
  console.log('[proxy] PUT params', context.params);
  return forward(request, context.params.slug ?? []);
}

export async function PATCH(request: NextRequest, context: { params: { slug?: string[] } }) {
  console.log('[proxy] PATCH params', context.params);
  return forward(request, context.params.slug ?? []);
}

export async function DELETE(request: NextRequest, context: { params: { slug?: string[] } }) {
  console.log('[proxy] DELETE params', context.params);
  return forward(request, context.params.slug ?? []);
}

export async function OPTIONS(request: NextRequest, context: { params: { slug?: string[] } }) {
  console.log('[proxy] OPTIONS params', context.params);
  return forward(request, context.params.slug ?? []);
}

