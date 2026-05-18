import { NextResponse } from "next/server";
import { promises as fs } from "fs";
import path from "path";

const CONFIG_PATH = path.join(process.cwd(), "config.local.json");

export async function GET() {
  try {
    const data = await fs.readFile(CONFIG_PATH, "utf-8");
    return NextResponse.json(JSON.parse(data));
  } catch {
    return NextResponse.json({
      endpointUrl: "http://localhost:11434/v1",
      apiKey: "",
      model: "qwen3:8b",
    });
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    await fs.writeFile(CONFIG_PATH, JSON.stringify(body, null, 2));
    return NextResponse.json({ ok: true });
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500 });
  }
}
