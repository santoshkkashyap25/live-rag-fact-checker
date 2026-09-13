import { NextRequest, NextResponse } from "next/server";

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const params = await context.params;
  return handleProxy(request, params);
}

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const params = await context.params;
  return handleProxy(request, params);
}

function getTargetBaseUrl(request: NextRequest): string {
  let raw = (
    process.env.BACKEND_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    ""
  ).trim();

  const reqHost =
    request.headers.get("x-forwarded-host") ||
    request.headers.get("host") ||
    "";

  // When running on Render Free Tier, internal hostnames (e.g. 'factguard-backend')
  // cannot communicate over private DNS without a paid plan.
  // Dynamically resolve the corresponding backend public URL if needed.
  if (
    reqHost.includes("onrender.com") &&
    (!raw || raw === "factguard-backend" || raw === "backend" || !raw.startsWith("http"))
  ) {
    if (raw.includes("onrender.com")) {
      return `https://${raw.replace(/^https?:\/\//, "")}`.replace(/\/$/, "");
    }
    const backendHost = reqHost.replace(/frontend/g, "backend");
    return `https://${backendHost}`;
  }

  if (!raw) {
    raw = "http://127.0.0.1:8000";
  }

  // Ensure valid scheme
  if (!raw.startsWith("http://") && !raw.startsWith("https://")) {
    if (raw.includes("onrender.com")) {
      raw = `https://${raw}`;
    } else if (raw.includes("localhost") || raw.includes("127.0.0.1")) {
      raw = `http://${raw}`;
    } else {
      raw = raw.includes(":") ? `http://${raw}` : `http://${raw}:8000`;
    }
  }

  return raw.replace(/\/$/, "");
}

async function handleProxy(
  request: NextRequest,
  resolvedParams: { path: string[] }
) {
  const backendBase = getTargetBaseUrl(request);
  const path = resolvedParams.path ? resolvedParams.path.join("/") : "";
  const targetUrl = `${backendBase}/api/${path}${request.nextUrl.search}`;
  console.log(`[Next.js API Proxy] ${request.method} -> ${targetUrl}`);

  try {
    const contentType = request.headers.get("content-type") || "application/json";
    const body =
      request.method !== "GET" && request.method !== "HEAD"
        ? await request.text()
        : undefined;

    const headers: Record<string, string> = {
      "Content-Type": contentType,
    };
    const userId = request.headers.get("x-user-id");
    if (userId) {
      headers["X-User-ID"] = userId;
    }
    const llmProvider = request.headers.get("x-llm-provider");
    if (llmProvider) {
      headers["X-LLM-Provider"] = llmProvider;
    }
    const llmApiKey = request.headers.get("x-llm-api-key");
    if (llmApiKey) {
      headers["X-LLM-API-Key"] = llmApiKey;
    }
    const llmModel = request.headers.get("x-llm-model");
    if (llmModel) {
      headers["X-LLM-Model"] = llmModel;
    }

    const maxAttempts = 3;
    let lastError: unknown = null;

    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        const response = await fetch(targetUrl, {
          method: request.method,
          headers,
          body,
        });

        const data = await response.text();
        return new NextResponse(data, {
          status: response.status,
          headers: {
            "Content-Type": response.headers.get("content-type") || "application/json",
          },
        });
      } catch (err: unknown) {
        lastError = err;
        const errorMsg = err instanceof Error ? err.message : String(err);
        const isConnError =
          errorMsg.includes("fetch failed") ||
          errorMsg.includes("ECONNREFUSED") ||
          errorMsg.includes("connect ECONNREFUSED") ||
          errorMsg.includes("ETIMEDOUT") ||
          errorMsg.includes("undici");

        if (isConnError && attempt < maxAttempts) {
          // Backend is likely in the final seconds of cold-start initialization
          await new Promise((resolve) => setTimeout(resolve, 1500));
          continue;
        }
        break;
      }
    }

    const errorMsg = lastError instanceof Error ? lastError.message : String(lastError);
    return NextResponse.json(
      {
        code: "BACKEND_WARMING_UP",
        detail:
          "FactGuard backend engine is initializing. Please wait a moment for container startup.",
        raw_error: errorMsg,
      },
      { status: 503 }
    );
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : String(err);
    return NextResponse.json(
      { detail: `Proxy error connecting to backend: ${errorMsg}` },
      { status: 502 }
    );
  }
}
