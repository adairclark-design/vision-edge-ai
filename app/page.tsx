"use client";

import { useState } from 'react';
import ImageUploader from './components/ImageUploader';
import HUDOverlay from './components/HUDOverlay';

// ─── Types ───────────────────────────────────────────────────────────────────

interface AnalysisV2 {
  scan_id: string;
  asset_ticker: string;
  current_price: number;
  confidence_score: number;
  edge_detected: boolean;
  status_message: string;
  disclaimer: string;
  market_structure_events?: any[];
  support_resistance_zones?: any[];
  fibonacci_levels?: any[];
  candlestick_signals?: any[];
  setup?: {
    trend_direction: string;
    position_direction: string;   // 'LONG' | 'SHORT'
    entry_zone: { min: number; max: number };
    invalidation_point: number;
    price_targets: number[];
    risk_reward_ratio: number;
    confluence_score: number;
    confluence_reasons: string[];
  } | null;
  svg_overlay?: any;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function trendBadge(direction: string) {
  if (direction === 'UPTREND') return { emoji: '▲', label: 'Uptrend', color: 'text-green-400', bg: 'bg-green-900/40 border-green-700' };
  if (direction === 'DOWNTREND') return { emoji: '▼', label: 'Downtrend', color: 'text-red-400', bg: 'bg-red-900/40 border-red-700' };
  return { emoji: '↔', label: 'Ranging', color: 'text-yellow-400', bg: 'bg-yellow-900/40 border-yellow-700' };
}

function rrColor(rr: number) {
  if (rr >= 2.0) return 'text-green-400';
  if (rr >= 1.5) return 'text-yellow-400';
  return 'text-red-400';
}

function confidenceBar(score: number) {
  if (score >= 80) return 'bg-green-500';
  if (score >= 60) return 'bg-yellow-500';
  return 'bg-red-500';
}

// ─── Dashboard Page ──────────────────────────────────────────────────────────

export default function Dashboard() {
  const [analysis, setAnalysis] = useState<AnalysisV2 | null>(null);
  const [imageUrl, setImageUrl] = useState<string | null>(null);

  const handleAnalysisComplete = (data: AnalysisV2, localImageUrl: string) => {
    setAnalysis(data);
    setImageUrl(localImageUrl);
  };

  const setup = analysis?.setup;
  const trend = setup ? trendBadge(setup.trend_direction) : null;
  const entryMid = setup ? (setup.entry_zone.min + setup.entry_zone.max) / 2 : 0;
  const isShort = setup?.position_direction === 'SHORT';

  return (
    <div className="min-h-screen bg-black text-gray-100 font-sans">

      {/* ── Header ── */}
      <header className="border-b border-gray-800 bg-black/50 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded bg-gradient-to-br from-blue-500 to-cyan-400 flex items-center justify-center">
              <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <h1 className="text-xl font-bold tracking-tight">VisionEdge <span className="text-blue-400">AI</span></h1>
          </div>
          <div className="text-xs font-mono text-gray-500 flex items-center space-x-4">
            <span className="flex items-center">
              <span className="w-2 h-2 rounded-full bg-green-500 mr-2 animate-pulse"></span>
              SYSTEM: ONLINE
            </span>
            <span>SCP v2.0</span>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">

        {/* ── Hero (no analysis yet) ── */}
        {!analysis && (
          <div className="text-center mb-12 space-y-4">
            <h2 className="text-5xl font-bold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-gray-100 to-gray-500">
              Zero-Latency Clarity
            </h2>
            <p className="text-gray-400 max-w-xl mx-auto">
              Upload a chart. Receive a structured 7-step technical analysis with confluence scoring, market structure events, Fibonacci levels, and a precise risk-reward setup.
            </p>
          </div>
        )}

        {!analysis && <ImageUploader onAnalysisComplete={handleAnalysisComplete} />}

        {/* ── Results: 2-column layout ── */}
        {analysis && imageUrl && (
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 items-start animate-in fade-in slide-in-from-bottom-4 duration-500">

            {/* LEFT: HUD Chart (3/5) */}
            <div className="lg:col-span-3">
              <HUDOverlay
                imageUrl={imageUrl}
                isNoise={!analysis.edge_detected}
                overlayData={analysis.svg_overlay}
                marketStructureEvents={analysis.market_structure_events}
                supportResistanceZones={analysis.support_resistance_zones}
                fibonacciLevels={analysis.fibonacci_levels}
                candlestickSignals={analysis.candlestick_signals}
                confidenceScore={analysis.confidence_score}
              />

              {/* Status message under chart */}
              <p className="text-gray-500 font-mono text-xs mt-3 leading-relaxed px-1">
                {analysis.status_message}
              </p>

              {/* ── LEFT CONTEXT CARDS: Current Price + Confluence + Structure ── */}
              {/* Current Price */}
              <div className="mt-4 bg-gray-900 border border-gray-800 p-5 rounded-xl">
                <span className="text-gray-500 font-mono text-xs uppercase tracking-wider block mb-1">Current Price</span>
                <span className="text-2xl font-mono text-blue-400">
                  {analysis.current_price > 0 ? `$${analysis.current_price.toFixed(2)}` : 'N/A'}
                </span>
              </div>

              {/* Confluence Signals */}
              {setup && (setup.confluence_reasons?.length ?? 0) > 0 && (
                <div className="bg-gray-900 border border-gray-800 p-5 rounded-xl">
                  <h3 className="text-xs font-mono text-gray-400 uppercase tracking-widest border-b border-gray-800 pb-2 mb-3">
                    Confluence Signals
                  </h3>
                  <ul className="space-y-2">
                    {setup.confluence_reasons.map((reason, i) => (
                      <li key={i} className="flex items-start space-x-2">
                        <span className="text-green-500 mt-0.5 flex-shrink-0">✓</span>
                        <span className="font-mono text-xs leading-relaxed text-gray-300">{reason}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Market Structure Events */}
              {(analysis.market_structure_events?.length ?? 0) > 0 && (
                <div className="bg-gray-900 border border-gray-800 p-5 rounded-xl">
                  <h3 className="text-xs font-mono text-gray-400 uppercase tracking-widest border-b border-gray-800 pb-2 mb-3">
                    Market Structure
                  </h3>
                  <ul className="space-y-2">
                    {analysis.market_structure_events!.map((e, i) => {
                      const isBullish = e.event_type?.includes('BULLISH');
                      const isBOS = e.event_type?.startsWith('BOS');
                      return (
                        <li key={i} className="flex items-start gap-2 text-xs">
                          <span className={`font-bold font-mono mt-0.5 ${isBullish ? 'text-purple-400' : 'text-orange-400'}`}>
                            {isBOS ? 'BOS' : 'CHOCH'} {isBullish ? '▲' : '▼'}
                          </span>
                          <span className="text-gray-400 font-mono leading-relaxed">{e.significance}</span>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              )}
            </div>

            {/* RIGHT: Action Panel (2/5) */}
            <div className="lg:col-span-2 flex flex-col gap-4">

              {/* Confidence */}
              <div className="bg-gray-900 border border-gray-800 p-5 rounded-xl">
                <span className="text-gray-500 font-mono text-xs uppercase tracking-wider block mb-3">Confluence Confidence</span>
                <div className="flex items-center justify-between mb-2">
                  <span className={`text-3xl font-bold ${analysis.confidence_score >= 80 ? 'text-green-400' : analysis.confidence_score >= 60 ? 'text-yellow-400' : 'text-red-400'}`}>
                    {analysis.confidence_score.toFixed(0)}%
                  </span>
                  {setup && (
                    <span className="text-gray-500 font-mono text-xs">
                      {setup.confluence_score} signals
                    </span>
                  )}
                </div>
                <div className="w-full h-1.5 bg-gray-800 rounded-full">
                  <div
                    className={`h-1.5 rounded-full transition-all duration-700 ${confidenceBar(analysis.confidence_score)}`}
                    style={{ width: `${analysis.confidence_score}%` }}
                  />
                </div>
              </div>

              {/* Trend Direction */}
              {trend && (
                <div className={`border p-4 rounded-xl ${trend.bg}`}>
                  <span className="text-gray-500 font-mono text-xs uppercase tracking-wider block mb-1">Trend Direction</span>
                  <span className={`text-xl font-bold font-mono ${trend.color}`}>
                    {trend.emoji} {trend.label}
                  </span>
                </div>
              )}

              {/* ── YOUR TRADE PLAN (right column, below Confidence + Trend) ── */}
              {setup && analysis.edge_detected && (
                <div className="rounded-xl overflow-hidden border border-gray-800">
                  {/* Header */}
                  <div className="bg-gray-900 px-5 py-3 flex items-center justify-between border-b border-gray-800">
                    <div className="flex items-center gap-2">
                      <span className="text-lg">{isShort ? '📉' : '📋'}</span>
                      <span className="text-white font-bold text-sm tracking-wide">YOUR TRADE PLAN</span>
                      <span className={`text-xs font-mono font-bold px-2 py-0.5 rounded ${isShort ? 'bg-red-900/60 text-red-400' : 'bg-green-900/60 text-green-400'}`}>
                        {isShort ? 'SHORT ▼' : 'LONG ▲'}
                      </span>
                    </div>
                    <span className="text-gray-500 font-mono text-xs">Execute in order ↓</span>
                  </div>

                  {/* Step 1 — ENTRY */}
                  <div className={`border-b px-5 py-4 ${isShort ? 'bg-red-950/60 border-red-900/40' : 'bg-green-950/60 border-green-900/40'}`}>
                    <div className="flex items-start gap-3">
                      <div className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 ${isShort ? 'bg-red-500' : 'bg-green-500'}`}>
                        <span className="text-black text-xs font-black">1</span>
                      </div>
                      <div className="flex-1">
                        <p className={`font-bold text-xs uppercase tracking-widest mb-1 ${isShort ? 'text-red-400' : 'text-green-400'}`}>
                          {isShort ? 'Sell / Short Here' : 'Buy / Enter Here'}
                        </p>
                        <p className={`font-mono text-xl font-bold ${isShort ? 'text-red-300' : 'text-green-300'}`}>
                          ${setup.entry_zone.min.toFixed(2)}
                          <span className={isShort ? 'text-red-600' : 'text-green-600'}> – </span>
                          ${setup.entry_zone.max.toFixed(2)}
                        </p>
                        <p className={`text-xs mt-1 font-mono ${isShort ? 'text-red-800' : 'text-green-700'}`}>
                          {isShort
                            ? 'Wait for price to reach this zone, then open your short position'
                            : 'Wait for price to reach this zone, then open your position'}
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Step 2 — STOP LOSS */}
                  <div className={`border-b px-5 py-4 ${isShort ? 'bg-green-950/30 border-green-900/30' : 'bg-red-950/50 border-red-900/40'}`}>
                    <div className="flex items-start gap-3">
                      <div className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 ${isShort ? 'bg-green-600' : 'bg-red-500'}`}>
                        <span className="text-black text-xs font-black">2</span>
                      </div>
                      <div className="flex-1">
                        <p className={`font-bold text-xs uppercase tracking-widest mb-1 ${isShort ? 'text-green-400' : 'text-red-400'}`}>
                          Stop Loss — Exit if Wrong
                        </p>
                        <p className={`font-mono text-xl font-bold ${isShort ? 'text-green-300' : 'text-red-300'}`}>
                          ${setup.invalidation_point.toFixed(2)}
                        </p>
                        <p className={`text-xs mt-1 font-mono ${isShort ? 'text-green-900' : 'text-red-800'}`}>
                          Set this the moment you enter. This caps your maximum loss.
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Step 3 — TAKE PROFIT */}
                  <div className="bg-blue-950/40 px-5 py-4">
                    <div className="flex items-start gap-3">
                      <div className="w-7 h-7 rounded-full bg-blue-500 flex items-center justify-center flex-shrink-0 mt-0.5">
                        <span className="text-black text-xs font-black">3</span>
                      </div>
                      <div className="flex-1">
                        <p className="text-blue-400 font-bold text-xs uppercase tracking-widest mb-2">
                          Take Profit — Lock In Gains
                        </p>
                        <div className="space-y-2">
                          {setup.price_targets.map((tp, i) => {
                            const rawPct = entryMid > 0 ? ((tp - entryMid) / entryMid * 100) : 0;
                            // For shorts, profit is when price drops — flip sign display
                            const displayPct = isShort ? -rawPct : rawPct;
                            const longLabels = ['Sell 1/3 of position', 'Sell another 1/3', 'Final exit — full close'];
                            const shortLabels = ['Buy back 1/3', 'Buy back another 1/3', 'Cover fully — full close'];
                            return (
                              <div key={i} className="flex items-center justify-between bg-blue-900/30 rounded-lg px-3 py-2">
                                <div>
                                  <span className="text-blue-400 font-mono text-xs font-bold">TP{i + 1}</span>
                                  <span className="text-gray-500 font-mono text-xs ml-2">
                                    {isShort ? (shortLabels[i] ?? 'Cover remainder') : (longLabels[i] ?? 'Exit remainder')}
                                  </span>
                                </div>
                                <div className="text-right">
                                  <span className="text-blue-200 font-mono font-bold text-sm">${tp.toFixed(2)}</span>
                                  {displayPct !== 0 && (
                                    <span className={`font-mono text-xs ml-2 ${displayPct > 0 ? 'text-green-500' : 'text-red-500'}`}>
                                      {displayPct > 0 ? '+' : ''}{displayPct.toFixed(1)}%
                                    </span>
                                  )}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* R:R Footer */}
                  <div className="bg-gray-900/80 px-5 py-3 flex items-center justify-between border-t border-gray-800">
                    <span className="text-gray-500 font-mono text-xs">Risk vs. Reward</span>
                    <span className={`font-bold font-mono text-lg ${setup.risk_reward_ratio >= 2 ? 'text-green-400' : setup.risk_reward_ratio >= 1.5 ? 'text-yellow-400' : 'text-red-400'}`}>
                      1 : {setup.risk_reward_ratio.toFixed(2)}
                      <span className="text-gray-600 text-xs ml-2 font-normal">
                        {setup.risk_reward_ratio >= 2 ? '✓ Excellent' : setup.risk_reward_ratio >= 1.5 ? '✓ Good' : '⚠ Marginal'}
                      </span>
                    </span>
                  </div>
                </div>
              )}

              {/* No edge state */}
              {!analysis.edge_detected && (
                <div className="bg-gray-900/60 border border-gray-800 rounded-xl px-5 py-6 text-center">
                  <span className="text-3xl mb-3 block">⏳</span>
                  <p className="text-gray-300 font-bold text-sm">No Clear Trade Right Now</p>
                  <p className="text-gray-600 font-mono text-xs mt-2 leading-relaxed">
                    Not enough confirming signals found.<br />
                    Try a different timeframe or wait for a clearer setup.
                  </p>
                </div>
              )}

              {/* Reset + Disclaimer */}
              <button
                onClick={() => { setAnalysis(null); setImageUrl(null); }}
                className="w-full px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded text-sm transition-colors font-mono"
              >
                [ RESET SCAN ]
              </button>
              <p className="text-xs text-gray-700 font-mono text-center leading-snug">
                {analysis.disclaimer}
              </p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
