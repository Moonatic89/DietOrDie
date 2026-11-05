import React, { useState, useEffect, useRef } from 'react';
import {
  X,
  Activity,
  Gauge,
  Flame,
  Zap,
  Timer,
  Sliders,
  ChevronRight,
  TrendingUp,
  Award
} from 'lucide-react';
import { RidePerformanceData, TelemetryPoint } from '../types';
import { getRidePerformance } from '../api';

interface RidePerformanceModalProps {
  rideId: number;
  onClose: () => void;
}

type MetricMode = 'all' | 'speed' | 'rpm' | 'watts';

export const RidePerformanceModal: React.FC<RidePerformanceModalProps> = ({
  rideId,
  onClose
}) => {
  const [data, setData] = useState<RidePerformanceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeMetric, setActiveMetric] = useState<MetricMode>('all');
  const [hoveredPoint, setHoveredPoint] = useState<TelemetryPoint | null>(null);
  const [hoverX, setHoverX] = useState<number | null>(null);

  const svgRef = useRef<SVGSVGElement | null>(null);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setError(null);

    getRidePerformance(rideId)
      .then((perf) => {
        if (isMounted) {
          setData(perf);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.message || 'Impossibile caricare le statistiche della pedalata');
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [rideId]);

  const formatSec = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  // SVG Chart Geometry
  const viewBoxWidth = 600;
  const viewBoxHeight = 220;
  const paddingLeft = 35;
  const paddingRight = 15;
  const paddingTop = 20;
  const paddingBottom = 30;

  const chartWidth = viewBoxWidth - paddingLeft - paddingRight;
  const chartHeight = viewBoxHeight - paddingTop - paddingBottom;

  const points = data?.telemetry_points || [];
  const maxSec = data ? Math.max(1, data.duration_seconds) : 1;

  // Max values for scale
  const maxSpeedScale = Math.max(30, (data?.max_speed_kmh || 25) * 1.15);
  const maxRpmScale = Math.max(100, (data?.max_rpm || 80) * 1.15);
  const maxWattsScale = Math.max(200, (data?.max_watts || 150) * 1.15);

  const getCoordinates = (p: TelemetryPoint) => {
    const x = paddingLeft + (p.sec / maxSec) * chartWidth;
    const ySpeed = paddingTop + chartHeight - (p.speed / maxSpeedScale) * chartHeight;
    const yRpm = paddingTop + chartHeight - (p.rpm / maxRpmScale) * chartHeight;
    const yWatts = paddingTop + chartHeight - (p.watts / maxWattsScale) * chartHeight;
    return { x, ySpeed, yRpm, yWatts };
  };

  // Build SVG path
  const buildSvgPath = (getY: (p: TelemetryPoint) => number) => {
    if (points.length === 0) return '';
    return points.reduce((acc, p, idx) => {
      const x = paddingLeft + (p.sec / maxSec) * chartWidth;
      const y = Math.min(paddingTop + chartHeight, Math.max(paddingTop, getY(p)));
      return idx === 0 ? `M ${x.toFixed(1)} ${y.toFixed(1)}` : `${acc} L ${x.toFixed(1)} ${y.toFixed(1)}`;
    }, '');
  };

  const pathSpeed = buildSvgPath((p) => paddingTop + chartHeight - (p.speed / maxSpeedScale) * chartHeight);
  const pathRpm = buildSvgPath((p) => paddingTop + chartHeight - (p.rpm / maxRpmScale) * chartHeight);
  const pathWatts = buildSvgPath((p) => paddingTop + chartHeight - (p.watts / maxWattsScale) * chartHeight);

  // Closed paths for area fill
  const buildAreaPath = (linePath: string) => {
    if (!linePath || points.length === 0) return '';
    const firstX = paddingLeft;
    const lastX = paddingLeft + (points[points.length - 1].sec / maxSec) * chartWidth;
    const baseline = paddingTop + chartHeight;
    return `${linePath} L ${lastX.toFixed(1)} ${baseline.toFixed(1)} L ${firstX.toFixed(1)} ${baseline.toFixed(1)} Z`;
  };

  const areaSpeed = buildAreaPath(pathSpeed);
  const areaRpm = buildAreaPath(pathRpm);
  const areaWatts = buildAreaPath(pathWatts);

  // Interaction handlers for crosshair tooltip
  const handlePointerMove = (e: React.PointerEvent<SVGSVGElement>) => {
    if (!svgRef.current || points.length === 0) return;
    const rect = svgRef.current.getBoundingClientRect();
    const clientX = e.clientX;
    const relX = clientX - rect.left;
    const svgX = (relX / rect.width) * viewBoxWidth;

    if (svgX < paddingLeft || svgX > viewBoxWidth - paddingRight) {
      setHoveredPoint(null);
      setHoverX(null);
      return;
    }

    const clampedRatio = Math.max(0, Math.min(1, (svgX - paddingLeft) / chartWidth));
    const targetSec = clampedRatio * maxSec;

    // Find nearest telemetry point
    let nearest = points[0];
    let minDiff = Math.abs(points[0].sec - targetSec);
    for (let i = 1; i < points.length; i++) {
      const diff = Math.abs(points[i].sec - targetSec);
      if (diff < minDiff) {
        minDiff = diff;
        nearest = points[i];
      }
    }

    setHoveredPoint(nearest);
    setHoverX(paddingLeft + (nearest.sec / maxSec) * chartWidth);
  };

  const handlePointerLeave = () => {
    setHoveredPoint(null);
    setHoverX(null);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5 bg-black/80 backdrop-blur-md animate-in fade-in">
      <div className="relative w-full max-w-2xl max-h-[92vh] overflow-y-auto rounded-3xl bg-zinc-950/95 border border-white/10 shadow-2xl shadow-emerald-950/40 p-4 sm:p-6 text-zinc-100 space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-white/10">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center shadow-inner">
              <Activity className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h2 className="text-base sm:text-lg font-black tracking-tight text-white">
                  Prestazioni Sessione #{rideId}
                </h2>
                <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                  Analisi
                </span>
              </div>
              {data && (
                <p className="text-xs text-zinc-400">
                  {data.distance_km} km in {Math.floor(data.duration_seconds / 60)}m {data.duration_seconds % 60}s • Livello {data.resistance_level}
                </p>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-xl bg-zinc-900 border border-white/10 hover:bg-zinc-800 text-zinc-400 hover:text-white flex items-center justify-center transition active:scale-95"
            aria-label="Chiudi"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {loading && (
          <div className="py-16 text-center space-y-3">
            <div className="inline-block w-8 h-8 border-3 border-emerald-400 border-t-transparent rounded-full animate-spin" />
            <p className="text-xs text-zinc-400">Elaborazione metriche telemetriche...</p>
          </div>
        )}

        {error && (
          <div className="p-4 rounded-2xl bg-rose-950/40 border border-rose-500/30 text-rose-300 text-xs">
            {error}
          </div>
        )}

        {data && !loading && (
          <>
            {/* KPI Stat Cards */}
            <div className="grid grid-cols-3 sm:grid-cols-6 gap-2 text-center">
              <div className="p-2.5 rounded-2xl bg-zinc-900/70 border border-white/5">
                <span className="text-[9px] uppercase font-bold text-zinc-400 block">Vel. Media</span>
                <span className="text-base sm:text-lg font-black text-emerald-400 font-mono">
                  {data.avg_speed_kmh}
                </span>
                <span className="text-[9px] text-zinc-500 block">km/h (max {data.max_speed_kmh})</span>
              </div>

              <div className="p-2.5 rounded-2xl bg-zinc-900/70 border border-white/5">
                <span className="text-[9px] uppercase font-bold text-zinc-400 block">Cadenza</span>
                <span className="text-base sm:text-lg font-black text-amber-400 font-mono">
                  {data.avg_rpm}
                </span>
                <span className="text-[9px] text-zinc-500 block">RPM (max {data.max_rpm})</span>
              </div>

              <div className="p-2.5 rounded-2xl bg-zinc-900/70 border border-white/5">
                <span className="text-[9px] uppercase font-bold text-zinc-400 block">Potenza</span>
                <span className="text-base sm:text-lg font-black text-purple-400 font-mono">
                  {data.avg_watts}
                </span>
                <span className="text-[9px] text-zinc-500 block">Watt (max {data.max_watts})</span>
              </div>

              <div className="p-2.5 rounded-2xl bg-zinc-900/70 border border-white/5">
                <span className="text-[9px] uppercase font-bold text-zinc-400 block">Pedalate</span>
                <span className="text-base sm:text-lg font-black text-cyan-400 font-mono">
                  {data.total_pedal_strokes}
                </span>
                <span className="text-[9px] text-zinc-500 block">giri totali</span>
              </div>

              <div className="p-2.5 rounded-2xl bg-zinc-900/70 border border-white/5">
                <span className="text-[9px] uppercase font-bold text-zinc-400 block">Energia</span>
                <span className="text-base sm:text-lg font-black text-rose-400 font-mono">
                  {Math.round(data.calories_burned)}
                </span>
                <span className="text-[9px] text-zinc-500 block">kcal stimate</span>
              </div>

              <div className="p-2.5 rounded-2xl bg-zinc-900/70 border border-white/5">
                <span className="text-[9px] uppercase font-bold text-zinc-400 block">Resistenza</span>
                <span className="text-base sm:text-lg font-black text-orange-400 font-mono">
                  R{data.resistance_level}
                </span>
                <span className="text-[9px] text-zinc-500 block">cyclette</span>
              </div>
            </div>

            {/* Performance Chart Card */}
            <div className="p-4 rounded-3xl bg-zinc-900/50 border border-white/5 space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center space-x-2">
                  <TrendingUp className="w-4 h-4 text-emerald-400" />
                  <span className="text-xs font-bold uppercase tracking-wider text-zinc-200">
                    Curva Telemetrica
                  </span>
                </div>

                {/* Metric Selector Buttons */}
                <div className="flex items-center space-x-1 bg-zinc-950/80 p-1 rounded-xl border border-white/5 text-[11px]">
                  <button
                    onClick={() => setActiveMetric('all')}
                    className={`px-2.5 py-1 rounded-lg font-bold transition ${
                      activeMetric === 'all'
                        ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                        : 'text-zinc-400 hover:text-white'
                    }`}
                  >
                    Tutto
                  </button>
                  <button
                    onClick={() => setActiveMetric('speed')}
                    className={`px-2 py-1 rounded-lg font-bold transition flex items-center space-x-1 ${
                      activeMetric === 'speed'
                        ? 'bg-emerald-500 text-zinc-950 shadow-sm'
                        : 'text-emerald-400/80 hover:text-emerald-300'
                    }`}
                  >
                    <span>Velocità</span>
                  </button>
                  <button
                    onClick={() => setActiveMetric('rpm')}
                    className={`px-2 py-1 rounded-lg font-bold transition flex items-center space-x-1 ${
                      activeMetric === 'rpm'
                        ? 'bg-amber-500 text-zinc-950 shadow-sm'
                        : 'text-amber-400/80 hover:text-amber-300'
                    }`}
                  >
                    <span>RPM</span>
                  </button>
                  <button
                    onClick={() => setActiveMetric('watts')}
                    className={`px-2 py-1 rounded-lg font-bold transition flex items-center space-x-1 ${
                      activeMetric === 'watts'
                        ? 'bg-purple-500 text-white shadow-sm'
                        : 'text-purple-400/80 hover:text-purple-300'
                    }`}
                  >
                    <span>Watts</span>
                  </button>
                </div>
              </div>

              {/* Interactive SVG Chart */}
              <div className="relative w-full aspect-[21/9] sm:aspect-[24/9] bg-zinc-950/90 rounded-2xl border border-white/5 overflow-hidden select-none">
                <svg
                  ref={svgRef}
                  viewBox={`0 0 ${viewBoxWidth} ${viewBoxHeight}`}
                  className="w-full h-full cursor-crosshair touch-none"
                  onPointerMove={handlePointerMove}
                  onPointerLeave={handlePointerLeave}
                >
                  <defs>
                    <linearGradient id="gradSpeed" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#10b981" stopOpacity="0.4" />
                      <stop offset="100%" stopColor="#10b981" stopOpacity="0.0" />
                    </linearGradient>
                    <linearGradient id="gradRpm" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#f59e0b" stopOpacity="0.35" />
                      <stop offset="100%" stopColor="#f59e0b" stopOpacity="0.0" />
                    </linearGradient>
                    <linearGradient id="gradWatts" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#a855f7" stopOpacity="0.35" />
                      <stop offset="100%" stopColor="#a855f7" stopOpacity="0.0" />
                    </linearGradient>
                  </defs>

                  {/* Horizontal Grid lines */}
                  {[0.25, 0.5, 0.75, 1.0].map((ratio) => {
                    const y = paddingTop + chartHeight * (1 - ratio);
                    return (
                      <g key={ratio}>
                        <line
                          x1={paddingLeft}
                          y1={y}
                          x2={viewBoxWidth - paddingRight}
                          y2={y}
                          stroke="#ffffff"
                          strokeOpacity="0.06"
                          strokeDasharray="3 3"
                        />
                        <text
                          x={paddingLeft - 6}
                          y={y + 3}
                          textAnchor="end"
                          fill="#71717a"
                          fontSize="9"
                          fontFamily="monospace"
                        >
                          {Math.round(
                            activeMetric === 'rpm'
                              ? maxRpmScale * ratio
                              : activeMetric === 'watts'
                              ? maxWattsScale * ratio
                              : maxSpeedScale * ratio
                          )}
                        </text>
                      </g>
                    );
                  })}

                  {/* Time Axis Labels */}
                  {[0, 0.25, 0.5, 0.75, 1.0].map((ratio) => {
                    const x = paddingLeft + chartWidth * ratio;
                    const sec = Math.round(maxSec * ratio);
                    return (
                      <text
                        key={ratio}
                        x={x}
                        y={viewBoxHeight - 8}
                        textAnchor="middle"
                        fill="#71717a"
                        fontSize="9"
                        fontFamily="monospace"
                      >
                        {formatSec(sec)}
                      </text>
                    );
                  })}

                  {/* Curves & Areas */}
                  {(activeMetric === 'all' || activeMetric === 'speed') && (
                    <>
                      <path d={areaSpeed} fill="url(#gradSpeed)" />
                      <path
                        d={pathSpeed}
                        fill="none"
                        stroke="#10b981"
                        strokeWidth="2.2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </>
                  )}

                  {(activeMetric === 'all' || activeMetric === 'rpm') && (
                    <>
                      {activeMetric === 'rpm' && <path d={areaRpm} fill="url(#gradRpm)" />}
                      <path
                        d={pathRpm}
                        fill="none"
                        stroke="#f59e0b"
                        strokeWidth={activeMetric === 'rpm' ? '2.2' : '1.5'}
                        strokeOpacity={activeMetric === 'all' ? '0.75' : '1.0'}
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </>
                  )}

                  {(activeMetric === 'all' || activeMetric === 'watts') && (
                    <>
                      {activeMetric === 'watts' && <path d={areaWatts} fill="url(#gradWatts)" />}
                      <path
                        d={pathWatts}
                        fill="none"
                        stroke="#c084fc"
                        strokeWidth={activeMetric === 'watts' ? '2.2' : '1.5'}
                        strokeOpacity={activeMetric === 'all' ? '0.75' : '1.0'}
                        strokeDasharray={activeMetric === 'all' ? '4 3' : 'none'}
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </>
                  )}

                  {/* Interactive Crosshair */}
                  {hoverX !== null && hoveredPoint && (
                    <g>
                      <line
                        x1={hoverX}
                        y1={paddingTop}
                        x2={hoverX}
                        y2={paddingTop + chartHeight}
                        stroke="#38bdf8"
                        strokeWidth="1.2"
                        strokeDasharray="2 2"
                      />
                      {/* Active points on lines */}
                      {(activeMetric === 'all' || activeMetric === 'speed') && (
                        <circle
                          cx={hoverX}
                          cy={paddingTop + chartHeight - (hoveredPoint.speed / maxSpeedScale) * chartHeight}
                          r="4"
                          fill="#10b981"
                          stroke="#ffffff"
                          strokeWidth="1.5"
                        />
                      )}
                      {(activeMetric === 'all' || activeMetric === 'rpm') && (
                        <circle
                          cx={hoverX}
                          cy={paddingTop + chartHeight - (hoveredPoint.rpm / maxRpmScale) * chartHeight}
                          r="4"
                          fill="#f59e0b"
                          stroke="#ffffff"
                          strokeWidth="1.5"
                        />
                      )}
                      {(activeMetric === 'all' || activeMetric === 'watts') && (
                        <circle
                          cx={hoverX}
                          cy={paddingTop + chartHeight - (hoveredPoint.watts / maxWattsScale) * chartHeight}
                          r="4"
                          fill="#c084fc"
                          stroke="#ffffff"
                          strokeWidth="1.5"
                        />
                      )}
                    </g>
                  )}
                </svg>

                {/* Floating Tooltip Box */}
                {hoveredPoint && (
                  <div className="absolute top-2 right-2 bg-zinc-950/90 border border-sky-400/30 rounded-xl p-2 px-3 text-[11px] font-mono shadow-xl backdrop-blur-sm pointer-events-none flex items-center space-x-3">
                    <div>
                      <span className="text-zinc-500 block text-[9px] uppercase">Tempo</span>
                      <span className="text-white font-bold">{formatSec(hoveredPoint.sec)}</span>
                    </div>
                    <div>
                      <span className="text-emerald-400 block text-[9px] uppercase">Vel.</span>
                      <span className="text-emerald-300 font-bold">{hoveredPoint.speed} km/h</span>
                    </div>
                    <div>
                      <span className="text-amber-400 block text-[9px] uppercase">RPM</span>
                      <span className="text-amber-300 font-bold">{hoveredPoint.rpm}</span>
                    </div>
                    <div>
                      <span className="text-purple-400 block text-[9px] uppercase">Potenza</span>
                      <span className="text-purple-300 font-bold">{hoveredPoint.watts} W</span>
                    </div>
                  </div>
                )}
              </div>

              {/* Legend */}
              <div className="flex items-center justify-center space-x-4 text-[10px] text-zinc-400 pt-1">
                <div className="flex items-center space-x-1.5">
                  <span className="w-3 h-0.5 bg-emerald-500 rounded" />
                  <span>Velocità (km/h)</span>
                </div>
                <div className="flex items-center space-x-1.5">
                  <span className="w-3 h-0.5 bg-amber-500 rounded" />
                  <span>Cadenza (RPM)</span>
                </div>
                <div className="flex items-center space-x-1.5">
                  <span className="w-3 h-0.5 bg-purple-400 rounded border-t border-dashed" />
                  <span>Potenza (Watts)</span>
                </div>
              </div>
            </div>

            {/* Aerobic & Intensity Zones */}
            <div className="p-4 rounded-3xl bg-zinc-900/50 border border-white/5 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-zinc-300 flex items-center space-x-1.5">
                  <Zap className="w-3.5 h-3.5 text-amber-400" />
                  <span>Distribuzione Zone d'Intensità</span>
                </span>
                <span className="text-[10px] text-zinc-500">
                  Target cardio su cadenza e velocità
                </span>
              </div>

              {/* Progress Bar Breakdown */}
              <div className="w-full h-3 rounded-full bg-zinc-950 overflow-hidden flex border border-white/10">
                <div
                  style={{ width: `${data.zones.zone1_pct}%` }}
                  className="h-full bg-sky-500 transition-all"
                  title={`Z1: ${data.zones.zone1_pct}%`}
                />
                <div
                  style={{ width: `${data.zones.zone2_pct}%` }}
                  className="h-full bg-emerald-500 transition-all"
                  title={`Z2: ${data.zones.zone2_pct}%`}
                />
                <div
                  style={{ width: `${data.zones.zone3_pct}%` }}
                  className="h-full bg-rose-500 transition-all"
                  title={`Z3: ${data.zones.zone3_pct}%`}
                />
              </div>

              {/* Zone Details */}
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div className="p-2.5 rounded-2xl bg-zinc-950/60 border border-sky-500/20">
                  <div className="flex items-center space-x-1.5 mb-1">
                    <span className="w-2 h-2 rounded-full bg-sky-400" />
                    <span className="text-[10px] font-bold text-sky-400 uppercase">Z1 Recupero</span>
                  </div>
                  <p className="text-[10px] text-zinc-400">&lt;15 km/h agile</p>
                  <p className="text-sm font-black text-white mt-1 font-mono">
                    {data.zones.zone1_pct}% <span className="text-[10px] font-normal text-zinc-500">({formatSec(data.zones.zone1_recovery_sec)})</span>
                  </p>
                </div>

                <div className="p-2.5 rounded-2xl bg-zinc-950/60 border border-emerald-500/20">
                  <div className="flex items-center space-x-1.5 mb-1">
                    <span className="w-2 h-2 rounded-full bg-emerald-400" />
                    <span className="text-[10px] font-bold text-emerald-400 uppercase">Z2 Bruciagrassi</span>
                  </div>
                  <p className="text-[10px] text-zinc-400">15-22 km/h aerobico</p>
                  <p className="text-sm font-black text-white mt-1 font-mono">
                    {data.zones.zone2_pct}% <span className="text-[10px] font-normal text-zinc-500">({formatSec(data.zones.zone2_aerobic_sec)})</span>
                  </p>
                </div>

                <div className="p-2.5 rounded-2xl bg-zinc-950/60 border border-rose-500/20">
                  <div className="flex items-center space-x-1.5 mb-1">
                    <span className="w-2 h-2 rounded-full bg-rose-400" />
                    <span className="text-[10px] font-bold text-rose-400 uppercase">Z3 Soglia</span>
                  </div>
                  <p className="text-[10px] text-zinc-400">&gt;22 km/h spinta</p>
                  <p className="text-sm font-black text-white mt-1 font-mono">
                    {data.zones.zone3_pct}% <span className="text-[10px] font-normal text-zinc-500">({formatSec(data.zones.zone3_threshold_sec)})</span>
                  </p>
                </div>
              </div>
            </div>

            {/* Splits Chilometrici */}
            {data.splits && data.splits.length > 0 && (
              <div className="p-4 rounded-3xl bg-zinc-900/50 border border-white/5 space-y-2.5">
                <span className="text-xs font-bold uppercase tracking-wider text-zinc-300 flex items-center space-x-1.5">
                  <Timer className="w-3.5 h-3.5 text-sky-400" />
                  <span>Passo per Chilometro (Splits)</span>
                </span>

                <div className="divide-y divide-white/5">
                  {data.splits.map((s) => (
                    <div
                      key={s.km}
                      className="py-2 flex items-center justify-between text-xs font-mono"
                    >
                      <div className="flex items-center space-x-2">
                        <span className="w-6 h-6 rounded-lg bg-zinc-800 text-zinc-300 flex items-center justify-center font-bold text-[10px]">
                          {s.km}
                        </span>
                        <span className="text-zinc-200 font-sans font-medium text-xs">
                          Km {s.km}
                        </span>
                      </div>

                      <div className="flex items-center space-x-4 text-right">
                        <div>
                          <span className="text-[9px] text-zinc-500 block uppercase">Tempo</span>
                          <span className="text-white font-bold">{formatSec(s.duration_seconds)}</span>
                        </div>
                        <div>
                          <span className="text-[9px] text-zinc-500 block uppercase">Media</span>
                          <span className="text-emerald-400 font-bold">{s.avg_speed_kmh} km/h</span>
                        </div>
                        <div>
                          <span className="text-[9px] text-zinc-500 block uppercase">Cadenza</span>
                          <span className="text-amber-400 font-bold">{Math.round(s.avg_rpm)} RPM</span>
                        </div>
                        <div className="hidden sm:block">
                          <span className="text-[9px] text-zinc-500 block uppercase">Potenza</span>
                          <span className="text-purple-400 font-bold">{Math.round(s.avg_watts)} W</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};
