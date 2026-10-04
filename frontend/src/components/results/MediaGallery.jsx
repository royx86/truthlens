import React, { useState } from 'react';
import { ChevronLeft, ChevronRight, Video, Image as ImageIcon } from 'lucide-react';

export function MediaGallery({ media = [] }) {
  const [activeIndex, setActiveIndex] = useState(0);

  if (!media || media.length === 0) {
    return (
      <div className="w-full h-48 bg-slate-100 rounded-xl flex flex-col items-center justify-center text-slate-400 border border-slate-200">
        <ImageIcon className="w-8 h-8 mb-1.5 opacity-60" />
        <span className="text-xs font-medium">No media available</span>
      </div>
    );
  }

  const currentMedia = media[activeIndex] || media[0];
  const isVideo = currentMedia?.type === 'video';
  const total = media.length;

  const handlePrev = (e) => {
    e.stopPropagation();
    setActiveIndex((prev) => (prev === 0 ? total - 1 : prev - 1));
  };

  const handleNext = (e) => {
    e.stopPropagation();
    setActiveIndex((prev) => (prev === total - 1 ? 0 : prev + 1));
  };

  return (
    <div className="space-y-3">
      {/* Main Media Container */}
      <div className="relative rounded-xl overflow-hidden bg-slate-950 aspect-[4/5] sm:aspect-square flex items-center justify-center group shadow-inner">
        {isVideo ? (
          currentMedia.url ? (
            <video
              src={currentMedia.url}
              controls
              className="w-full h-full object-contain"
              poster={currentMedia.thumbnail_url}
            >
              Your browser does not support video playback.
            </video>
          ) : (
            <div className="flex flex-col items-center text-slate-400">
              <Video className="w-12 h-12 mb-2 text-slate-500" />
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                Video Post
              </span>
            </div>
          )
        ) : (
          <img
            src={currentMedia.url || currentMedia.thumbnail_url}
            alt={currentMedia.visual_analysis?.description || 'Social post media'}
            loading="lazy"
            className="w-full h-full object-cover select-none"
            onError={(e) => {
              e.target.onerror = null;
              e.target.src = 'https://placehold.co/600x600/e2e8f0/475569?text=Media+Preview';
            }}
          />
        )}

        {/* Previous/Next Arrows (only when > 1 item) */}
        {total > 1 && (
          <>
            <button
              type="button"
              onClick={handlePrev}
              aria-label="Previous image"
              className="absolute left-2.5 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-black/60 hover:bg-black/80 text-white flex items-center justify-center transition-all opacity-80 hover:opacity-100 backdrop-blur-sm cursor-pointer"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              type="button"
              onClick={handleNext}
              aria-label="Next image"
              className="absolute right-2.5 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-black/60 hover:bg-black/80 text-white flex items-center justify-center transition-all opacity-80 hover:opacity-100 backdrop-blur-sm cursor-pointer"
            >
              <ChevronRight className="w-4 h-4" />
            </button>

            {/* Counter Badge */}
            <div className="absolute bottom-2.5 right-2.5 px-2 py-0.5 rounded-md bg-black/70 backdrop-blur-sm text-white text-[11px] font-semibold tracking-wider">
              {activeIndex + 1} / {total}
            </div>
          </>
        )}
      </div>

      {/* Thumbnails row (if > 1 media item) */}
      {total > 1 && (
        <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-thin">
          {media.map((item, idx) => {
            const isActive = idx === activeIndex;
            return (
              <button
                key={idx}
                type="button"
                onClick={() => setActiveIndex(idx)}
                aria-label={`View media ${idx + 1}`}
                className={`relative w-12 h-12 rounded-lg overflow-hidden shrink-0 border-2 transition-all cursor-pointer ${
                  isActive
                    ? 'border-violet-600 ring-2 ring-violet-500/20 scale-105'
                    : 'border-transparent opacity-70 hover:opacity-100'
                }`}
              >
                <img
                  src={item.thumbnail_url || item.url}
                  alt={`Thumbnail ${idx + 1}`}
                  className="w-full h-full object-cover"
                />
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
