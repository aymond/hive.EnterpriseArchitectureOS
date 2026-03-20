"use client";

import React, { useEffect, useRef } from 'react';
import mermaid from 'mermaid';
import { ZoomIn, ZoomOut, RotateCcw, Maximize2 } from 'lucide-react';
import { TransformWrapper, TransformComponent } from 'react-zoom-pan-pinch';

interface MermaidProps {
  chart: string;
}

const Mermaid: React.FC<MermaidProps> = ({ chart }) => {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let isMounted = true;
    
    mermaid.initialize({
      startOnLoad: false,
      theme: 'dark',
      securityLevel: 'loose',
      fontFamily: 'Inter, system-ui, sans-serif',
      themeVariables: {
        primaryColor: '#6366f1',
        primaryTextColor: '#fff',
        primaryBorderColor: '#4338ca',
        lineColor: '#818cf8',
        secondaryColor: '#1e1b4b',
        tertiaryColor: '#0f172a'
      }
    });

    const renderChart = async () => {
      if (!ref.current) return;
      
      try {
        // Create a unique ID for this specific render
        const id = `mermaid-${Math.random().toString(36).substr(2, 9)}`;
        const { svg } = await mermaid.render(id, chart);
        
        if (isMounted && ref.current) {
          ref.current.innerHTML = svg;
          const svgElement = ref.current.querySelector('svg');
          if (svgElement) {
            svgElement.style.maxWidth = '1000%'; // Allow it to be much larger than parent
            svgElement.style.width = 'auto'; // Use natural width
            svgElement.style.minWidth = '800px'; // Ensure it's not tiny
            svgElement.style.height = 'auto';
            svgElement.style.display = 'block';
            svgElement.style.cursor = 'grab';
          }
        }
      } catch (error) {
        console.error('Mermaid rendering failed:', error);
        if (isMounted && ref.current) {
          ref.current.innerHTML = `<div class="text-red-500 font-mono text-xs p-4 bg-red-500/10 rounded-xl border border-red-500/20">
            <p class="font-bold mb-2">Mermaid Syntax Error</p>
            <pre class="whitespace-pre-wrap">${chart}</pre>
          </div>`;
        }
      }
    };

    renderChart();
    
    return () => {
      isMounted = false;
    };
  }, [chart]);

  const handlePopout = () => {
    if (ref.current) {
      const svg = ref.current.querySelector('svg');
      if (svg) {
        const svgData = new XMLSerializer().serializeToString(svg);
        const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
        const url = URL.createObjectURL(svgBlob);
        window.open(url, '_blank');
      }
    }
  };

  return (
    <div className="relative group/mermaid my-12">
      <div className="flex justify-center p-2 rounded-[2.5rem] bg-neutral-950/50 border border-neutral-800 overflow-hidden relative min-h-[500px]">
        <TransformWrapper
          initialScale={0.7}
          minScale={0.1}
          maxScale={5}
          centerOnInit={true}
          limitToBounds={false}
        >
          {({ zoomIn, zoomOut, resetTransform }: { zoomIn: (step?: number) => void; zoomOut: (step?: number) => void; resetTransform: () => void }) => (
            <>
              {/* Controls UI */}
              <div className="absolute bottom-6 right-6 z-10 flex items-center gap-2 p-2 rounded-2xl bg-neutral-900/80 backdrop-blur-xl border border-neutral-800 shadow-2xl opacity-0 group-hover/mermaid:opacity-100 transition-all duration-500 translate-y-2 group-hover/mermaid:translate-y-0">
                <button onClick={() => zoomIn()} className="p-2 hover:bg-neutral-800 rounded-xl text-neutral-400 hover:text-indigo-400 transition" title="Zoom In">
                  <ZoomIn size={18} />
                </button>
                <button onClick={() => zoomOut()} className="p-2 hover:bg-neutral-800 rounded-xl text-neutral-400 hover:text-indigo-400 transition" title="Zoom Out">
                  <ZoomOut size={18} />
                </button>
                <button onClick={() => resetTransform()} className="p-2 hover:bg-neutral-800 rounded-xl text-neutral-400 hover:text-indigo-400 transition" title="Reset View">
                  <RotateCcw size={18} />
                </button>
                <div className="w-px h-6 bg-neutral-800 mx-1" />
                <button onClick={handlePopout} className="p-2 hover:bg-neutral-800 rounded-xl text-neutral-400 hover:text-emerald-400 transition" title="Popout into new tab">
                  <Maximize2 size={18} />
                </button>
              </div>

              <TransformComponent wrapperClass="!w-full !h-full" contentClass="flex justify-center items-center min-w-full min-h-[500px]">
                <div className="mermaid-container" ref={ref}>
                  <div className="animate-pulse text-indigo-400 font-black text-[10px] tracking-[0.3em] uppercase">Rendering Architecture...</div>
                </div>
              </TransformComponent>
            </>
          )}
        </TransformWrapper>
      </div>
      
      {/* Legend / Info HUD */}
      <div className="absolute top-6 left-6 pointer-events-none opacity-0 group-hover/mermaid:opacity-100 transition-all duration-500 -translate-y-2 group-hover/mermaid:translate-y-0">
        <div className="px-4 py-2 rounded-xl bg-indigo-500/10 backdrop-blur-md border border-indigo-500/20 text-indigo-400 text-[9px] font-black tracking-widest uppercase shadow-xl ring-1 ring-indigo-500/20">
          Interactive Capability Map • Drag to browse • Scroll to zoom
        </div>
      </div>
    </div>
  );
};

export default Mermaid;
