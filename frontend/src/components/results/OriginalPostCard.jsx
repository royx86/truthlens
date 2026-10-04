import React, { useState } from 'react';
import { ExternalLink, Heart, MessageSquare, AlertOctagon, User } from 'lucide-react';
import { MediaGallery } from './MediaGallery';

export function OriginalPostCard({ author, source, content, context }) {
  const [isExpanded, setIsExpanded] = useState(false);

  const postText = content?.text || '';
  const isLongText = postText.length > 320;
  const displayedText = isExpanded || !isLongText ? postText : `${postText.slice(0, 300)}...`;

  const likes = content?.likes;
  const comments = content?.comments;

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-5 sm:p-6 shadow-sm space-y-5">
      <h2 className="text-base font-bold text-slate-900 pb-1">
        Original Post Details
      </h2>

      {/* Author Header */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          {author?.profileImageUrl ? (
            <img
              src={author.profileImageUrl}
              alt={author.name || 'Author avatar'}
              className="w-10 h-10 rounded-full object-cover border border-slate-200 shrink-0"
            />
          ) : (
            <div className="w-10 h-10 rounded-full bg-violet-100 text-violet-700 flex items-center justify-center font-bold text-sm shrink-0 uppercase">
              {author?.initials || <User className="w-5 h-5 text-violet-600" />}
            </div>
          )}

          <div className="min-w-0">
            <h3 className="text-sm font-bold text-slate-900 truncate">
              {author?.username || author?.name || 'Social Post Author'}
            </h3>
            <p className="text-xs text-slate-400 capitalize">
              {source?.platform || 'Social Media'}
            </p>
          </div>
        </div>

        {/* Link to Original Post */}
        {source?.url && (
          <a
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
            title="View original post"
            aria-label="View original post on platform"
            className="p-2 rounded-lg text-slate-400 hover:text-violet-600 hover:bg-slate-50 transition-colors shrink-0"
          >
            <ExternalLink className="w-4 h-4 stroke-[2.2]" />
          </a>
        )}
      </div>

      {/* Media Carousel / Gallery */}
      <MediaGallery media={content?.media} />

      {/* Context Flags Badge (Section 13) */}
      {context?.isSatire && (
        <div className="p-2.5 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 text-xs flex items-center gap-2">
          <AlertOctagon className="w-4 h-4 text-amber-600 shrink-0" />
          <span className="font-semibold">Satire / parody context detected</span>
        </div>
      )}

      {/* Post Text */}
      {postText ? (
        <div className="space-y-2 pt-1 border-t border-slate-100">
          <p className="text-xs sm:text-sm text-slate-700 whitespace-pre-line leading-relaxed font-normal">
            {displayedText}
          </p>

          {isLongText && (
            <button
              type="button"
              onClick={() => setIsExpanded(!isExpanded)}
              className="text-xs font-semibold text-violet-600 hover:text-violet-800 transition-colors cursor-pointer"
            >
              {isExpanded ? 'Show less' : 'Show more'}
            </button>
          )}
        </div>
      ) : (
        <div className="text-xs text-slate-400 italic pt-1 border-t border-slate-100">
          No caption text accompanied this post.
        </div>
      )}

      {/* Engagement Metadata */}
      {(likes !== null || comments !== null) && (
        <div className="flex items-center gap-5 pt-3 border-t border-slate-100 text-xs font-medium text-slate-500">
          {likes !== null && likes !== undefined && (
            <div className="flex items-center gap-1.5 hover:text-rose-600 transition-colors">
              <Heart className="w-4 h-4 text-rose-500" />
              <span>{Number(likes).toLocaleString()} likes</span>
            </div>
          )}
          {comments !== null && comments !== undefined && (
            <div className="flex items-center gap-1.5 hover:text-violet-600 transition-colors">
              <MessageSquare className="w-4 h-4 text-violet-500" />
              <span>{Number(comments).toLocaleString()} comments</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
