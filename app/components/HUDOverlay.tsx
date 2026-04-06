'use client';

// ─── Type Definitions ────────────────────────────────────────────────────────

interface Coordinate {
    x1: number; y1: number; x2: number; y2: number;
}
interface SvgProperties {
    strokeColor: string; fillColor: string; label: string;
}
interface SvgElement {
    type: string;
    coordinates: Coordinate;
    properties: SvgProperties;
}
interface SvgOverlayData {
    viewBox: string;
    elements: SvgElement[];
}
interface MarketStructureEvent {
    event_type: string;
    coordinates: Coordinate;
    significance: string;
}
interface SupportResistanceZone {
    price_level: number;
    zone_type: string;
    strength: number;
    coordinates: Coordinate;
}
interface FibonacciLevel {
    level: number;
    price: number;
    coordinates: Coordinate;
    is_key_level: boolean;
}
interface CandlestickSignal {
    pattern: string;
    at_key_zone: boolean;
    coordinates: Coordinate;
}

interface HUDOverlayProps {
    imageUrl: string;
    isNoise: boolean;
    overlayData?: SvgOverlayData | null;
    marketStructureEvents?: MarketStructureEvent[];
    supportResistanceZones?: SupportResistanceZone[];
    fibonacciLevels?: FibonacciLevel[];
    candlestickSignals?: CandlestickSignal[];
    confidenceScore?: number;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function confidenceBorderColor(score: number): string {
    if (score >= 80) return '#22c55e';  // green-500
    if (score >= 60) return '#eab308';  // yellow-500
    return '#ef4444';                    // red-500
}

function truncateLabel(label: string, maxLen = 18): string {
    return label.length > maxLen ? label.slice(0, maxLen) + '…' : label;
}

// ─── BOS/CHOCH Marker ───────────────────────────────────────────────────────

function BosChochMarker({ event, index }: { event: MarketStructureEvent; index: number }) {
    const c = event.coordinates;
    const isBullish = event.event_type.includes('BULLISH');
    const isBOS = event.event_type.startsWith('BOS');
    const color = isBullish ? '#a855f7' : '#f97316';  // purple / orange
    const label = isBOS ? (isBullish ? 'BOS ▲' : 'BOS ▼') : (isBullish ? 'CHOCH ▲' : 'CHOCH ▼');

    const midX = (c.x1 + c.x2) / 2;
    const midY = (c.y1 + c.y2) / 2;

    return (
        <g key={`ms-${index}`}>
            {/* Arrow line */}
            <line x1={c.x1} y1={c.y1} x2={c.x2} y2={c.y2}
                stroke={color} strokeWidth="2" strokeDasharray="4,4" opacity="0.85" />
            {/* Label badge */}
            <rect x={midX - 28} y={midY - 12} width={56} height={18}
                fill={color} rx="3" opacity="0.85" />
            <text x={midX} y={midY + 3} textAnchor="middle"
                fill="white" fontSize="10" fontFamily="monospace" fontWeight="bold">
                {label}
            </text>
        </g>
    );
}

// ─── S/R Zone Band ───────────────────────────────────────────────────────────

function SRZoneBand({ zone, index }: { zone: SupportResistanceZone; index: number }) {
    const c = zone.coordinates;
    const isSupport = zone.zone_type === 'SUPPORT';
    const fill = isSupport ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.15)';
    const stroke = isSupport ? '#22c55e' : '#ef4444';
    const width = c.x2 - c.x1;
    const height = Math.max(Math.abs(c.y2 - c.y1), 6);
    const y = Math.min(c.y1, c.y2);
    const opacity = 0.5 + (zone.strength / 10);

    return (
        <g key={`sr-${index}`} opacity={opacity}>
            <rect x={c.x1} y={y} width={width} height={height}
                fill={fill} stroke={stroke} strokeWidth="1.5" />
            {/* Strength indicator dots */}
            {Array.from({ length: zone.strength }).map((_, i) => (
                <circle key={i} cx={c.x1 + 8 + i * 8} cy={y + height / 2}
                    r="3" fill={stroke} opacity="0.8" />
            ))}
            <text x={c.x2 - 4} y={y - 4} textAnchor="end"
                fill={stroke} fontSize="11" fontFamily="monospace" fontWeight="bold">
                {zone.zone_type} {zone.price_level.toFixed(2)}
            </text>
        </g>
    );
}

// ─── Fibonacci Level Line ────────────────────────────────────────────────────

function FibLine({ fib, index, viewBoxWidth }: { fib: FibonacciLevel; index: number; viewBoxWidth: number }) {
    const y = fib.coordinates.y1;
    const isKey = fib.is_key_level;
    const color = isKey ? '#f59e0b' : '#6366f1';  // amber / indigo
    const strokeWidth = isKey ? 1.5 : 0.8;
    const dashArray = isKey ? '8,4' : '4,4';
    const label = `${(fib.level * 100).toFixed(1)}%  ${fib.price.toFixed(2)}`;

    return (
        <g key={`fib-${index}`} opacity={isKey ? 0.9 : 0.55}>
            <line x1={0} y1={y} x2={viewBoxWidth} y2={y}
                stroke={color} strokeWidth={strokeWidth} strokeDasharray={dashArray} />
            <rect x={viewBoxWidth - 100} y={y - 10} width={98} height={16}
                fill="rgba(0,0,0,0.6)" rx="2" />
            <text x={viewBoxWidth - 52} y={y + 3} textAnchor="middle"
                fill={color} fontSize="10" fontFamily="monospace">
                {label}
            </text>
        </g>
    );
}

// ─── Candlestick Signal Marker ───────────────────────────────────────────────

function CandleSignalMarker({ signal, index }: { signal: CandlestickSignal; index: number }) {
    const c = signal.coordinates;
    const isBullish = signal.pattern.includes('BULL') || signal.pattern === 'HAMMER' || signal.pattern === 'MORNING_STAR';
    const color = isBullish ? '#22c55e' : '#ef4444';
    const arrowY = isBullish ? c.y2 + 18 : c.y1 - 18;
    const arrow = isBullish ? '▲' : '▼';
    const centerX = (c.x1 + c.x2) / 2;

    return (
        <g key={`cs-${index}`} opacity={signal.at_key_zone ? 0.95 : 0.65}>
            {/* Outline box around the candle pattern */}
            <rect x={c.x1 - 2} y={Math.min(c.y1, c.y2) - 2}
                width={Math.abs(c.x2 - c.x1) + 4} height={Math.abs(c.y2 - c.y1) + 4}
                fill="none" stroke={color} strokeWidth={signal.at_key_zone ? 2 : 1}
                strokeDasharray="3,2" rx="2" />
            {/* Pattern label */}
            <text x={centerX} y={arrowY} textAnchor="middle"
                fill={color} fontSize="10" fontFamily="monospace">
                {arrow} {signal.pattern.replace(/_/g, ' ')}
            </text>
        </g>
    );
}

// ─── Main HUD Overlay ────────────────────────────────────────────────────────

export default function HUDOverlay({
    imageUrl,
    isNoise,
    overlayData,
    marketStructureEvents = [],
    supportResistanceZones = [],
    fibonacciLevels = [],
    candlestickSignals = [],
    confidenceScore = 0,
}: HUDOverlayProps) {
    const borderColor = confidenceBorderColor(confidenceScore);

    // Parse viewBox dimensions
    let viewBoxWidth = 1920;
    let viewBoxHeight = 1080;
    if (overlayData?.viewBox) {
        const parts = overlayData.viewBox.split(' ');
        if (parts.length === 4) {
            viewBoxWidth = parseFloat(parts[2]) || 1920;
            viewBoxHeight = parseFloat(parts[3]) || 1080;
        }
    }

    return (
        <div
            className="relative w-full overflow-hidden rounded-xl bg-black mt-4"
            style={{ border: `2px solid ${borderColor}`, boxShadow: `0 0 20px ${borderColor}33` }}
        >
            {/* Base Image */}
            <img
                src={imageUrl}
                alt="Analyzed Financial Chart"
                className={`w-full h-auto object-contain ${isNoise ? 'opacity-30 blur-sm' : 'opacity-100'}`}
            />

            {/* Noise Overlay Message */}
            {isNoise && (
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                    <div className="bg-red-900/80 backdrop-blur border border-red-500 p-6 rounded-xl shadow-2xl">
                        <h2 className="text-xl font-mono text-red-200 uppercase font-bold tracking-widest text-center">
                            Noise Detected
                        </h2>
                        <p className="text-red-300 font-mono text-sm mt-2 text-center">
                            Confluence &lt; 3 signals | No High-Probability Edge Identified
                        </p>
                    </div>
                </div>
            )}

            {/* SVG HUD Layer */}
            {!isNoise && (
                <svg
                    viewBox={overlayData?.viewBox || `0 0 ${viewBoxWidth} ${viewBoxHeight}`}
                    className="absolute inset-0 w-full h-full pointer-events-none"
                    preserveAspectRatio="none"
                >
                    {/* Layer 1: S/R Zones (bottom layer) */}
                    {supportResistanceZones.map((zone, i) => (
                        <SRZoneBand key={`sr-${i}`} zone={zone} index={i} />
                    ))}

                    {/* Layer 2: Fibonacci Levels */}
                    {fibonacciLevels.map((fib, i) => (
                        <FibLine key={`fib-${i}`} fib={fib} index={i} viewBoxWidth={viewBoxWidth} />
                    ))}

                    {/* Layer 3: SVG overlay elements from Gemini (entry, targets, invalidation) */}
                    {overlayData?.elements?.map((el, index) => {
                        const { coordinates: c, properties: p } = el;
                        if (el.type === 'rect') {
                            const width = Math.abs(c.x2 - c.x1);
                            const height = Math.max(Math.abs(c.y2 - c.y1), 4);
                            const x = Math.min(c.x1, c.x2);
                            const y = Math.min(c.y1, c.y2);
                            return (
                                <g key={`el-${index}`}>
                                    <rect x={x} y={y} width={width} height={height}
                                        fill={p.fillColor} stroke={p.strokeColor} strokeWidth="2" />
                                    {p.label && (
                                        <text x={x + 6} y={y - 8} fill={p.strokeColor}
                                            fontSize="22" fontFamily="monospace" fontWeight="bold">
                                            {truncateLabel(p.label)}
                                        </text>
                                    )}
                                </g>
                            );
                        }
                        if (el.type === 'line') {
                            const isInvalidation = p.label?.toLowerCase().includes('invalid') || p.strokeColor === 'red' || p.strokeColor === '#ef4444';
                            const isTarget = p.label?.toLowerCase().includes('tp') || p.label?.toLowerCase().includes('target');
                            return (
                                <g key={`el-${index}`}>
                                    <line x1={c.x1} y1={c.y1} x2={c.x2} y2={c.y2}
                                        stroke={p.strokeColor} strokeWidth={isInvalidation ? 3 : 2}
                                        strokeDasharray={isInvalidation ? '12,6' : isTarget ? '6,4' : '0'} />
                                    {p.label && (
                                        <text x={c.x2 + 8} y={c.y2 + 4} fill={p.strokeColor}
                                            fontSize="22" fontFamily="monospace" fontWeight="bold">
                                            {truncateLabel(p.label)}
                                        </text>
                                    )}
                                </g>
                            );
                        }
                        return null;
                    })}

                    {/* Layer 4: BOS/CHOCH Markers */}
                    {marketStructureEvents.map((event, i) => (
                        <BosChochMarker key={`bos-${i}`} event={event} index={i} />
                    ))}

                    {/* Layer 5: Candlestick Pattern Markers (top layer) */}
                    {candlestickSignals.map((signal, i) => (
                        <CandleSignalMarker key={`cs-${i}`} signal={signal} index={i} />
                    ))}
                </svg>
            )}

            {/* Confidence Score Badge */}
            {!isNoise && confidenceScore > 0 && (
                <div
                    className="absolute top-3 right-3 px-3 py-1 rounded-full text-xs font-mono font-bold"
                    style={{ backgroundColor: `${borderColor}33`, color: borderColor, border: `1px solid ${borderColor}` }}
                >
                    {confidenceScore.toFixed(0)}% CONFIDENCE
                </div>
            )}
        </div>
    );
}
