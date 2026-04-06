'use client';

import { useState, useEffect, useCallback, useRef } from 'react';

// ── Analysis stage definitions for the live progress indicator ──────────────
const STAGES = [
    { label: 'Macro Bias', durationMs: 6000 },
    { label: 'Trend Direction', durationMs: 8000 },
    { label: 'Market Structure', durationMs: 12000 },
    { label: 'S/R Zones', durationMs: 10000 },
    { label: 'Fibonacci Levels', durationMs: 8000 },
    { label: 'Candle Patterns', durationMs: 8000 },
    { label: 'Confluence Score', durationMs: 10000 },
    { label: 'SVG Overlay', durationMs: 8000 },
];
const TOTAL_DURATION_MS = STAGES.reduce((sum, s) => sum + s.durationMs, 0);

const TIMEFRAMES = ['1m', '5m', '15m', '30m', '1H', '4H', 'Daily', 'Weekly'];

export default function ImageUploader({ onAnalysisComplete }: { onAnalysisComplete: (data: any, imageUrl: string) => void }) {
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [error, setError] = useState<string | null>(null);
    // Entry chart staging (file held here until user clicks Start Analysis)
    const [entryFile, setEntryFile] = useState<File | null>(null);
    const [entryPreview, setEntryPreview] = useState<string | null>(null);
    const [pasteHint, setPasteHint] = useState(false);

    // Timeframe + macro chart state
    const [timeframe, setTimeframe] = useState('4H');
    const [macroFile, setMacroFile] = useState<File | null>(null);
    const [macroPreview, setMacroPreview] = useState<string | null>(null);
    const [macroTimeframe, setMacroTimeframe] = useState('Daily');
    // Hover-based paste routing: tracks which zone the mouse is currently over
    const hoveredZone = useRef<'entry' | 'macro' | null>(null);
    const [entryPasteHint, setEntryPasteHint] = useState(false);
    const [macroPasteHint, setMacroPasteHint] = useState(false);

    // Progress indicator state
    const [progress, setProgress] = useState(0);
    const [stageIndex, setStageIndex] = useState(0);
    const progressRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const startTimeRef = useRef<number>(0);

    const stageCount = STAGES.length;
    const currentStage = stageIndex < stageCount
        ? `Step ${stageIndex + 1}/${stageCount} — ${STAGES[stageIndex].label}…`
        : 'Finalising output…';

    // ── Progress timer ──────────────────────────────────────────────────────
    const startProgress = useCallback(() => {
        setProgress(0);
        setStageIndex(0);
        startTimeRef.current = Date.now();

        progressRef.current = setInterval(() => {
            const elapsed = Date.now() - startTimeRef.current;
            const raw = Math.min((elapsed / TOTAL_DURATION_MS) * 95, 95);
            setProgress(raw);

            let acc = 0;
            let idx = 0;
            for (const stage of STAGES) {
                acc += stage.durationMs;
                if (elapsed < acc) break;
                idx++;
            }
            setStageIndex(Math.min(idx, STAGES.length - 1));
        }, 200);
    }, []);

    const stopProgress = useCallback((success: boolean) => {
        if (progressRef.current) {
            clearInterval(progressRef.current);
            progressRef.current = null;
        }
        if (success) {
            setProgress(100);
            setStageIndex(STAGES.length);
        }
    }, []);

    useEffect(() => {
        return () => { if (progressRef.current) clearInterval(progressRef.current); };
    }, []);

    // ── Entry chart helpers ─────────────────────────────────────────────────
    const stageEntryImage = (file: File) => {
        if (entryPreview) URL.revokeObjectURL(entryPreview);
        setEntryFile(file);
        setEntryPreview(URL.createObjectURL(file));
        setError(null);
    };

    const clearEntry = () => {
        if (entryPreview) URL.revokeObjectURL(entryPreview);
        setEntryFile(null);
        setEntryPreview(null);
    };

    // ── Macro chart helpers ─────────────────────────────────────────────────
    const setMacroImage = (file: File) => {
        setMacroFile(file);
        setMacroPreview(URL.createObjectURL(file));
    };

    const clearMacro = () => {
        if (macroPreview) URL.revokeObjectURL(macroPreview);
        setMacroFile(null);
        setMacroPreview(null);
    };

    // ── Core submit handler (called by Start Analysis button) ───────────────
    const submitImage = useCallback(async (file: File) => {
        const imageUrl = URL.createObjectURL(file);
        setIsAnalyzing(true);
        setError(null);
        startProgress();

        const formData = new FormData();
        formData.append('image', file);
        formData.append('assetTicker', 'UNKNOWN');
        formData.append('timeframe', timeframe);
        if (macroFile) {
            formData.append('macroImage', macroFile);
            formData.append('macroTimeframe', macroTimeframe);
        }

        try {
            const response = await fetch('/api/scan', { method: 'POST', body: formData });

            if (!response.ok) {
                let errorBody = response.statusText;
                try {
                    const errData = await response.json();
                    errorBody = errData.details || errData.error || errorBody;
                } catch (_) { /* ignore */ }
                throw new Error(`API Error: ${errorBody}`);
            }

            const data = await response.json();
            stopProgress(true);
            await new Promise(r => setTimeout(r, 400));
            onAnalysisComplete(data, imageUrl);
        } catch (err: any) {
            console.error(err);
            stopProgress(false);
            setError(err.message || 'Failed to analyze chart');
        } finally {
            setIsAnalyzing(false);
        }
    }, [onAnalysisComplete, startProgress, stopProgress, timeframe, macroFile]);

    const handleStartAnalysis = () => {
        if (entryFile) submitImage(entryFile);
    };

    // ── File input (entry chart — stages, does NOT submit) ──────────────────
    const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) stageEntryImage(file);
        e.target.value = '';  // allow re-selecting same file
    };

    // ── Drag & drop (entry chart) ───────────────────────────────────────────
    const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        const file = e.dataTransfer.files?.[0];
        if (file && file.type.startsWith('image/')) stageEntryImage(file);
    };
    const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => e.preventDefault();

    // ── Global paste (Cmd+V) ────────────────────────────────────────────────
    // Routes to whichever zone the mouse is currently hovering over.
    useEffect(() => {
        const handlePaste = (e: ClipboardEvent) => {
            if (isAnalyzing) return;
            const items = e.clipboardData?.items;
            if (!items) return;
            for (const item of Array.from(items)) {
                if (item.type.startsWith('image/')) {
                    const file = item.getAsFile();
                    if (file) {
                        if (hoveredZone.current === 'macro') {
                            setMacroPasteHint(true);
                            setTimeout(() => setMacroPasteHint(false), 600);
                            setMacroImage(file);
                        } else {
                            // Default: entry chart slot
                            setEntryPasteHint(true);
                            setTimeout(() => setEntryPasteHint(false), 600);
                            stageEntryImage(file);
                        }
                        return;
                    }
                }
            }
        };
        window.addEventListener('paste', handlePaste);
        return () => window.removeEventListener('paste', handlePaste);
    }, [isAnalyzing, stageEntryImage]);

    // ── ANALYZING STATE ─────────────────────────────────────────────────────
    if (isAnalyzing) {
        return (
            <div className="flex flex-col items-center space-y-5 w-full max-w-2xl mx-auto py-10 px-6 border border-gray-800 rounded-xl bg-gray-900/50">
                <div className="relative w-16 h-16">
                    <div className="w-16 h-16 border-4 border-gray-800 rounded-full absolute inset-0" />
                    <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin absolute inset-0" />
                    <div className="absolute inset-0 flex items-center justify-center">
                        <span className="text-blue-400 text-xs font-mono font-bold">{Math.round(progress)}%</span>
                    </div>
                </div>

                <div className="text-center space-y-1">
                    <p className="text-blue-300 font-mono text-sm font-semibold">{currentStage}</p>
                    <p className="text-gray-600 font-mono text-xs">
                        Claude 3.5 Sonnet · SCP v2.0
                        {macroFile && <span className="text-cyan-700 ml-1">· Multi-Timeframe</span>}
                    </p>
                </div>

                <div className="w-full max-w-xs">
                    <div className="w-full h-1 bg-gray-800 rounded-full overflow-hidden">
                        <div
                            className="h-1 bg-gradient-to-r from-blue-600 to-cyan-400 rounded-full transition-all duration-500 ease-out"
                            style={{ width: `${progress}%` }}
                        />
                    </div>
                </div>

                <div className="grid grid-cols-2 gap-x-8 gap-y-1.5 text-left">
                    {STAGES.map((stage, i) => {
                        const isDone = i < stageIndex;
                        const isActive = i === stageIndex;
                        return (
                            <div key={i} className={`flex items-center gap-2 text-xs font-mono transition-colors duration-300 ${isDone ? 'text-green-500' : isActive ? 'text-blue-400' : 'text-gray-700'}`}>
                                <span className="flex-shrink-0 w-3">{isDone ? '✓' : isActive ? '▶' : '○'}</span>
                                <span>{stage.label}</span>
                            </div>
                        );
                    })}
                </div>
            </div>
        );
    }

    // ── IDLE STATE ──────────────────────────────────────────────────────────
    return (
        <div className="w-full max-w-2xl mx-auto space-y-3">

            {/* ── Row 1: Timeframe selector ── */}
            <div className="flex items-center gap-3 px-1">
                <span className="text-gray-500 font-mono text-xs uppercase tracking-wider whitespace-nowrap">Chart Timeframe</span>
                <div className="flex flex-wrap gap-1.5">
                    {TIMEFRAMES.map(tf => (
                        <button
                            key={tf}
                            onClick={() => setTimeframe(tf)}
                            className={`px-3 py-1 rounded font-mono text-xs transition-all duration-150 border ${timeframe === tf
                                ? 'bg-blue-600 border-blue-500 text-white'
                                : 'bg-gray-900 border-gray-700 text-gray-400 hover:border-gray-500 hover:text-gray-300'
                                }`}
                        >
                            {tf}
                        </button>
                    ))}
                </div>
            </div>

            {/* ── Row 2: Entry chart ── */}
            {entryFile && entryPreview ? (
                /* STAGED — show thumbnail + option to swap */
                <div className="rounded-xl border border-blue-800/50 overflow-hidden">
                    <div className="bg-gray-900 px-4 py-2.5 flex items-center justify-between border-b border-gray-800">
                        <div className="flex items-center gap-2">
                            <span className="bg-blue-600 text-white font-mono text-xs font-bold px-2.5 py-1 rounded uppercase tracking-wider">{timeframe} Chart</span>
                            <span className="text-green-400 font-mono text-xs">✓ Ready</span>
                        </div>
                        <label className="text-gray-500 hover:text-gray-300 font-mono text-xs cursor-pointer transition-colors">
                            Swap ↺
                            <input type="file" className="hidden" accept="image/*" onChange={handleFileUpload} />
                        </label>
                    </div>
                    <div className="flex items-center gap-4 px-4 py-3 bg-gray-950/60">
                        <img src={entryPreview} alt="Entry chart" className="h-20 w-auto rounded border border-gray-700 object-cover flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                            <p className="text-gray-300 font-mono text-xs font-bold truncate">{entryFile.name}</p>
                            <p className="text-gray-600 font-mono text-xs mt-0.5">{(entryFile.size / 1024).toFixed(0)} KB · {timeframe}</p>
                            {macroFile && <p className="text-cyan-700 font-mono text-xs mt-1">+ Macro chart attached</p>}
                        </div>
                        <button onClick={clearEntry} className="text-gray-700 hover:text-red-400 font-mono text-xs transition-colors flex-shrink-0">✕</button>
                    </div>
                </div>
            ) : (
                /* EMPTY — drop/paste zone */
                <div
                    onDrop={handleDrop}
                    onDragOver={handleDragOver}
                    onMouseEnter={() => { hoveredZone.current = 'entry'; }}
                    onMouseLeave={() => { hoveredZone.current = null; }}
                    className={`flex flex-col items-center justify-center p-8 border-2 border-dashed rounded-xl w-full transition-all duration-200 ${entryPasteHint ? 'border-blue-400 bg-blue-900/20' : 'border-gray-700 bg-gray-900/50 hover:bg-gray-800/50 hover:border-gray-600'
                        }`}
                >
                    <label className="flex flex-col items-center cursor-pointer space-y-4 w-full">
                        <div className="flex items-center gap-3">
                            <span className="bg-blue-600 text-white font-mono text-xs font-bold px-2.5 py-1 rounded uppercase tracking-wider">{timeframe} Chart</span>
                            <span className="text-gray-400 font-mono text-xs">Required · Entry chart</span>
                        </div>
                        <svg className="w-10 h-10 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                                d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
                        </svg>
                        <div className="text-center">
                            <span className="text-gray-200 font-semibold font-mono text-sm">Upload or Paste Your Entry Chart</span>
                            <p className="text-gray-500 text-xs mt-1">
                                Drag &amp; drop, click to browse, or{' '}
                                <kbd className="bg-gray-800 border border-gray-600 text-gray-300 font-mono text-xs px-1.5 py-0.5 rounded">⌘V</kbd>
                                {' '}to paste
                            </p>
                        </div>
                        <input type="file" className="hidden" accept="image/*" onChange={handleFileUpload} />
                    </label>
                </div>
            )}

            {/* ── Row 3: Optional Macro Chart ── */}
            <div className="rounded-xl border border-gray-800 overflow-hidden">
                {/* Header: label + remove button */}
                <div className="bg-gray-900/80 px-4 py-2.5 flex items-center justify-between border-b border-gray-800">
                    <div className="flex items-center gap-2">
                        <span className="text-cyan-500 font-mono text-xs font-bold uppercase tracking-wider">📈 Macro Chart</span>
                        <span className="text-gray-600 font-mono text-xs">Optional · Significantly improves accuracy</span>
                    </div>
                    {macroFile && (
                        <button onClick={clearMacro} className="text-gray-600 hover:text-red-400 font-mono text-xs transition-colors">
                            ✕ Remove
                        </button>
                    )}
                </div>
                {/* Timeframe selector — identical style to entry chart */}
                <div className="flex items-center gap-3 px-4 py-2.5 border-b border-gray-800 bg-gray-900/40">
                    <span className="text-gray-500 font-mono text-xs uppercase tracking-wider whitespace-nowrap">Chart Timeframe</span>
                    <div className="flex flex-wrap gap-1.5">
                        {TIMEFRAMES.map(tf => (
                            <button
                                key={tf}
                                onClick={() => setMacroTimeframe(tf)}
                                className={`px-3 py-1 rounded font-mono text-xs transition-all duration-150 border ${macroTimeframe === tf
                                    ? 'bg-cyan-600 border-cyan-500 text-white'
                                    : 'bg-gray-900 border-gray-700 text-gray-400 hover:border-gray-500 hover:text-gray-300'
                                    }`}
                            >
                                {tf}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Content */}
                {macroFile && macroPreview ? (
                    /* Preview */
                    <div className="relative bg-gray-950 p-3 flex items-center gap-3">
                        <img src={macroPreview} alt="Macro chart" className="h-16 w-auto rounded border border-gray-700 object-cover" />
                        <div>
                            <p className="text-gray-300 font-mono text-xs font-bold">Macro context chart loaded</p>
                            <p className="text-gray-600 font-mono text-xs mt-0.5">{macroFile.name} · {macroTimeframe}</p>
                            <p className="text-cyan-700 font-mono text-xs mt-1">✓ Multi-timeframe analysis enabled</p>
                        </div>
                    </div>
                ) : (
                    /* Full drop zone — hover to activate paste routing */
                    <div
                        onMouseEnter={() => { hoveredZone.current = 'macro'; }}
                        onMouseLeave={() => { hoveredZone.current = null; }}
                        onDrop={(e) => {
                            e.preventDefault();
                            const file = e.dataTransfer.files?.[0];
                            if (file && file.type.startsWith('image/')) setMacroImage(file);
                        }}
                        onDragOver={(e) => e.preventDefault()}
                        className={`flex flex-col items-center justify-center p-6 border-2 border-dashed rounded-b-xl cursor-pointer transition-all duration-200 ${macroPasteHint
                            ? 'border-cyan-400 bg-cyan-900/20'
                            : 'border-gray-800 bg-gray-950/50 hover:bg-gray-900/50 hover:border-cyan-800/60'
                            }`}
                    >
                        <label className="flex flex-col items-center gap-3 cursor-pointer w-full">
                            <svg className="w-8 h-8 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                                    d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
                            </svg>
                            <div className="text-center">
                                <p className="text-gray-400 font-mono text-xs">Drag &amp; drop, click to browse, or hover here and press <kbd className="bg-gray-800 border border-gray-700 text-gray-300 font-mono text-xs px-1.5 py-0.5 rounded">⌘V</kbd></p>
                                <p className="text-gray-700 font-mono text-xs mt-1">Daily or Weekly chart of the same asset</p>
                            </div>
                            <input
                                type="file"
                                className="hidden"
                                accept="image/*"
                                onChange={(e) => {
                                    const file = e.target.files?.[0];
                                    if (file) setMacroImage(file);
                                }}
                            />
                        </label>
                    </div>
                )}
            </div>

            {/* ── Start Analysis button ── */}
            <button
                onClick={handleStartAnalysis}
                disabled={!entryFile}
                className={`w-full py-3.5 rounded-xl font-mono font-bold text-sm tracking-wide transition-all duration-200 ${entryFile
                    ? 'bg-gradient-to-r from-blue-600 to-cyan-500 text-white hover:from-blue-500 hover:to-cyan-400 shadow-lg shadow-blue-900/30 hover:shadow-blue-800/40'
                    : 'bg-gray-900 text-gray-700 border border-gray-800 cursor-not-allowed'
                    }`}
            >
                {entryFile ? (
                    <span className="flex items-center justify-center gap-2">
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                        Start Analysis{macroFile ? ' · Multi-Timeframe' : ''}
                    </span>
                ) : (
                    'Upload a chart to begin'
                )}
            </button>

            {/* ── Error display ── */}
            {error && (
                <pre className="text-red-400 text-xs font-mono bg-red-900/20 border border-red-800 px-4 py-2 rounded-lg max-w-full overflow-auto whitespace-pre-wrap break-words">
                    {error}
                </pre>
            )}
        </div>
    );
}
