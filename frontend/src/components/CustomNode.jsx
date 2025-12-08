import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';
import { FileText, Box, PlayCircle, ExternalLink, Loader2, AlertCircle } from 'lucide-react';

const CustomNode = memo(({ data, selected }) => {
  // Apple-style: Subtle gradients, backdrop blur, smooth shadows
  
  const isVideo = !!data.video_id;
  const isLoading = data.status === 'loading';
  const isError = data.status === 'error';

  if (isLoading) {
      return (
        <div className="relative rounded-2xl w-64 h-32 overflow-hidden shadow-xl ring-1 ring-white/10 backdrop-blur-md bg-gray-900/60 flex items-center justify-center">
            {/* Shimmer Effect */}
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent animate-shimmer" style={{ backgroundSize: '200% 100%' }} />
            <div className="flex flex-col items-center gap-3 z-10">
                <Loader2 className="w-8 h-8 text-blue-400 animate-spin" />
                <span className="text-xs font-medium text-gray-300 tracking-wide animate-pulse">Analyzing Video...</span>
            </div>
        </div>
      );
  }

  if (isError) {
      return (
        <div className="relative rounded-2xl w-64 overflow-hidden shadow-xl ring-1 ring-red-500/50 backdrop-blur-md bg-red-900/20 p-4">
            <div className="flex items-start gap-3">
                <AlertCircle className="w-6 h-6 text-red-400 shrink-0" />
                <div>
                    <h3 className="text-sm font-bold text-red-200">Ingestion Failed</h3>
                    <p className="text-[10px] text-red-300/80 mt-1 leading-relaxed">
                        {data.error || "Unable to process content."}
                    </p>
                </div>
            </div>
            {/* Handle just so it's connectable if user wants to keep the error node? Or maybe not needed */}
            <Handle type="target" position={Position.Left} className="!bg-red-500/50 border-0" />
            <Handle type="source" position={Position.Right} className="!bg-red-500/50 border-0" />
        </div>
      );
  }

  return (
    <div className={`relative group transition-all duration-300 ease-out
        ${selected 
            ? 'scale-105 ring-2 ring-blue-500/50 shadow-[0_0_20px_rgba(59,130,246,0.3)]' 
            : 'hover:scale-102 hover:shadow-lg'
        }
    `}>
      {/* Glassmorphism Container */}
      <div className="
        backdrop-blur-xl bg-gray-900/90 
        border border-white/10 
        rounded-2xl 
        overflow-hidden
        w-64
        shadow-xl
        flex flex-col
      ">
        {/* Video/Image Thumbnail Header */}
        {(isVideo || data.thumbnail) ? (
            <div className="relative h-36 w-full group/video cursor-pointer">
                <img 
                    src={data.thumbnail || `https://img.youtube.com/vi/${data.video_id}/mqdefault.jpg`} 
                    alt="Thumbnail" 
                    className="w-full h-full object-cover opacity-80 group-hover/video:opacity-100 transition-opacity"
                />
                {isVideo ? (
                    <div className="absolute inset-0 flex items-center justify-center bg-black/20 group-hover/video:bg-black/40 transition-colors">
                        <PlayCircle className="w-12 h-12 text-white/90 drop-shadow-lg transform group-hover/video:scale-110 transition-transform" />
                    </div>
                ) : (
                    <div className="absolute inset-0 bg-gradient-to-t from-gray-900 via-transparent to-transparent opacity-60" />
                )}
                
                {/* External Link Overlay */}
                {isVideo && (
                    <a 
                        href={`https://www.youtube.com/watch?v=${data.video_id}`} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="absolute top-2 right-2 p-1.5 bg-black/60 rounded-full text-white/80 hover:bg-black/80 hover:text-white transition-colors"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <ExternalLink size={12} />
                    </a>
                )}
                
                {/* Module Badge Overlay */}
                <div className={`absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r ${
                    data.module === 'Payments' ? 'from-green-400 to-emerald-600' :
                    data.module === 'Auth' ? 'from-purple-400 to-pink-600' :
                    'from-blue-400 to-indigo-600'
                }`} />
            </div>
        ) : (
            /* Standard Header Gradient */
            <div className={`h-1.5 w-full bg-gradient-to-r ${
                data.module === 'Payments' ? 'from-green-400 to-emerald-600' :
                data.module === 'Auth' ? 'from-purple-400 to-pink-600' :
                'from-blue-400 to-indigo-600'
            }`} />
        )}

        <div className="p-4 pt-3">
            {/* Icon & Type (Only for non-video/image or small footer) */}
            {!isVideo && !data.thumbnail && (
                <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2 text-gray-400">
                        {data.type === 'module' ? <Box size={14} /> : <FileText size={14} />}
                        <span className="text-[10px] uppercase tracking-wider font-semibold opacity-70">
                            {data.module || 'General'}
                        </span>
                    </div>
                </div>
            )}

            {/* Title */}
            <h3 className={`text-sm font-medium text-gray-100 leading-snug line-clamp-2 mb-2 ${(isVideo || data.thumbnail) ? 'mt-1' : ''}`}>
                {data.title || data.label}
            </h3>

            {/* Summary */}
            {data.summary && (
                <p className="text-[11px] text-gray-400 line-clamp-2 leading-relaxed border-t border-white/5 pt-2 mt-2">
                    {data.summary}
                </p>
            )}
        </div>
      </div>

      {/* Handles */}
      <Handle type="target" position={Position.Left} className="w-3 h-3 !bg-blue-500/50 border-0 !opacity-0 group-hover:!opacity-100 transition-opacity" />
      <Handle type="source" position={Position.Right} className="w-3 h-3 !bg-blue-500/50 border-0 !opacity-0 group-hover:!opacity-100 transition-opacity" />
    </div>
  );
});

export default CustomNode;

