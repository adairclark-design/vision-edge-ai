import { NextResponse } from "next/server";
import { exec } from "child_process";
import { promisify } from "util";
import fs from "fs/promises";
import path from "path";
import crypto from "crypto";

const execAsync = promisify(exec);

export async function POST(req: Request) {
    const tmpFiles: string[] = [];

    try {
        const formData = await req.formData();
        const image = formData.get("image") as File;
        const macroImage = formData.get("macroImage") as File | null;
        const assetTicker = formData.get("assetTicker") as string || "UNKNOWN";
        const timeframe = formData.get("timeframe") as string || "4H";
        const macroTimeframe = formData.get("macroTimeframe") as string || "Daily";

        if (!image) {
            return NextResponse.json(
                { error: "Image file is required" },
                { status: 400 }
            );
        }

        // Ensure .tmp dir exists
        const tmpDir = path.join(process.cwd(), ".tmp");
        await fs.mkdir(tmpDir, { recursive: true });

        // Save entry chart
        const entryExt = image.name.split('.').pop() || 'png';
        const entryFilename = `${crypto.randomUUID()}.${entryExt}`;
        const entryFilePath = path.join(tmpDir, entryFilename);
        await fs.writeFile(entryFilePath, Buffer.from(await image.arrayBuffer()));
        tmpFiles.push(entryFilePath);

        // Save macro chart (optional)
        let macroFilePath: string | null = null;
        if (macroImage && macroImage.size > 0) {
            const macroExt = macroImage.name.split('.').pop() || 'png';
            const macroFilename = `${crypto.randomUUID()}.${macroExt}`;
            macroFilePath = path.join(tmpDir, macroFilename);
            await fs.writeFile(macroFilePath, Buffer.from(await macroImage.arrayBuffer()));
            tmpFiles.push(macroFilePath);
        }

        // Build payload for the Layer 3 Python tool
        const payload = JSON.stringify({
            image_path: entryFilePath,
            macro_image_path: macroFilePath,
            asset_ticker: assetTicker,
            timeframe: timeframe,
            macro_timeframe: macroTimeframe,
            mime_type: image.type || 'image/png',
            macro_mime_type: macroImage?.type || 'image/png',
            timestamp: new Date().toISOString()
        });

        const command = `echo '${payload.replace(/'/g, "'\\''")}' | /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 tools/analyze_chart.py`;

        try {
            const { stdout, stderr } = await execAsync(command, {
                cwd: process.cwd(),
                timeout: 180000,
                env: { ...process.env, PATH: process.env.PATH || '' }
            });

            if (stderr && !stdout) {
                console.error('Python Stderr:', stderr);
                return NextResponse.json({ error: 'Analysis pipeline failed', details: stderr }, { status: 500 });
            }

            const result = JSON.parse(stdout);

            if (result.status_message && result.status_message.includes("Failed to parse")) {
                return NextResponse.json({ error: 'Analysis pipeline failed', details: result.status_message }, { status: 500 });
            }

            return NextResponse.json(result);

        } catch (error: any) {
            console.error("Layer 3 Tool Execution Failed:", error);

            if (error.killed && error.signal === 'SIGTERM') {
                return NextResponse.json(
                    { error: "Analysis timed out", details: "Claude took longer than 180 seconds to process the chart." },
                    { status: 504 }
                );
            }

            const details = error.stderr || error.stdout || error.message;
            return NextResponse.json({ error: "Analysis pipeline failed", details }, { status: 500 });
        }

    } catch (error: any) {
        console.error("API Route Error:", error);
        return NextResponse.json({ error: "Failed to process request" }, { status: 500 });

    } finally {
        // Always clean up tmp files
        for (const f of tmpFiles) {
            fs.unlink(f).catch(() => { });
        }
    }
}
