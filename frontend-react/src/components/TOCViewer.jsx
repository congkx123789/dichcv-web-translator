import React, { useState, useEffect, useRef } from 'react';
import { Search, Globe, ChevronRight, ArrowRight, BookOpen, Sparkles, Layers, X } from 'lucide-react';
import { api } from '../utils/api';

export default function TOCViewer({ novelData, setNovelData, currentChapter, setCurrentChapter, isOpen, onClose }) {
  const [search, setSearch] = useState('');
  const [jumpInput, setJumpInput] = useState('');
  const [isTranslating, setIsTranslating] = useState(false);
  const activeBtnRef = useRef(null);

  const chapters = novelData.chapters || [];
  const filtered = chapters.filter(c => 
    c.title.toLowerCase().includes(search.toLowerCase()) || 
    `chương ${c.index + 1}`.includes(search.toLowerCase()) ||
    `${c.index + 1}` === search.trim()
  );

  // Auto-scroll active chapter into view smoothly when drawer opens
  useEffect(() => {
    if (isOpen && activeBtnRef.current) {
      setTimeout(() => {
        activeBtnRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }, 150);
    }
  }, [currentChapter, isOpen]);

  const handleTranslateTOC = async () => {
    setIsTranslating(true);
    try {
      let newChapters = [...novelData.chapters];
      let newMetadata = { ...novelData.metadata };
      
      for await (const data of api.translateTocStream(novelData.metadata, novelData.chapters)) {
        if (data.type === 'metadata') {
          newMetadata = data.metadata;
          setNovelData(prev => ({ ...prev, metadata: newMetadata }));
        } else if (data.type === 'chunk') {
          for (const chap of data.chapters) {
            if (chap.index >= 0 && chap.index < newChapters.length) {
              newChapters[chap.index] = chap;
            }
          }
          setNovelData(prev => ({ ...prev, chapters: [...newChapters] }));
        }
      }
    } catch (e) {
      alert("Lỗi dịch TOC: " + e.message);
    } finally {
      setIsTranslating(false);
    }
  };

  const handleJump = (e) => {
    e.preventDefault();
    const chapNum = parseInt(jumpInput, 10);
    if (!isNaN(chapNum) && chapNum >= 1 && chapNum <= chapters.length) {
      setCurrentChapter(chapNum - 1);
      setJumpInput('');
      if (onClose) onClose();
    } else {
      alert(`Vui lòng nhập số chương từ 1 đến ${chapters.length}`);
    }
  };

  const handleSelectChapter = (idx) => {
    setCurrentChapter(idx);
    if (onClose) onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop overlay */}
      <div 
        className="fixed inset-0 bg-black/75 backdrop-blur-md transition-opacity duration-300"
        onClick={onClose}
      />

      {/* Off-canvas Drawer Panel */}
      <aside className="fixed inset-y-0 left-0 w-full max-w-sm sm:w-96 bg-slate-900 shadow-2xl flex flex-col z-50 border-r border-slate-800 transform transition-transform duration-300 ease-out">
        {/* Novel Info & Close Header */}
        <div className="p-4 border-b border-slate-800 bg-slate-950/80 z-10 space-y-3">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <h2 className="font-bold text-base text-slate-100 truncate leading-snug" title={novelData.metadata.title}>
                {novelData.metadata.title}
              </h2>
              <p className="text-xs text-slate-400 truncate mt-0.5" title={novelData.metadata.author}>
                ✍️ {novelData.metadata.author || 'Tác giả'}
              </p>
            </div>
            
            <div className="flex items-center gap-2 flex-shrink-0">
              <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded-full border border-indigo-500/20">
                <Layers className="w-3 h-3" />
                {chapters.length} chương
              </span>
              
              <button
                onClick={onClose}
                className="p-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
                title="Đóng mục lục (Esc)"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Quick Search & Jump */}
          <div className="grid grid-cols-5 gap-2">
            <div className="relative col-span-3">
              <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                type="text"
                placeholder="Tìm tên/số chương..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 text-xs rounded-xl py-2 pl-8 pr-3 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-slate-200 transition-all placeholder:text-slate-500"
              />
            </div>

            <form onSubmit={handleJump} className="col-span-2 relative flex items-center">
              <input
                type="number"
                min="1"
                max={chapters.length}
                placeholder="Chương..."
                value={jumpInput}
                onChange={e => setJumpInput(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 text-xs rounded-xl py-2 pl-2.5 pr-6 text-slate-200 focus:outline-none focus:border-indigo-500 transition-all placeholder:text-slate-500"
              />
              <button type="submit" className="absolute right-2 text-slate-400 hover:text-indigo-400 transition-colors">
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </form>
          </div>

          {/* Translate TOC Button */}
          <button
            onClick={handleTranslateTOC}
            disabled={isTranslating}
            className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-indigo-500/15 to-blue-500/15 hover:from-indigo-500/25 hover:to-blue-500/25 text-indigo-300 py-2 rounded-xl text-xs font-semibold transition-all border border-indigo-500/30 shadow-sm disabled:opacity-50 active:scale-[0.98]"
          >
            {isTranslating ? (
              <>
                <Sparkles className="w-3.5 h-3.5 animate-spin text-indigo-400" />
                Đang tự động dịch danh mục...
              </>
            ) : (
              <>
                <Globe className="w-3.5 h-3.5 text-indigo-400" />
                Dịch Tên Chương & Meta (AI)
              </>
            )}
          </button>
        </div>

        {/* Chapters Interactive Button Cards */}
        <div className="flex-1 overflow-y-auto p-3 space-y-1.5 scroll-smooth custom-scrollbar">
          {filtered.map((chap) => {
            const isActive = currentChapter === chap.index;
            return (
              <button
                key={chap.index}
                ref={isActive ? activeBtnRef : null}
                onClick={() => handleSelectChapter(chap.index)}
                className={`w-full text-left p-3 rounded-xl transition-all duration-200 group flex flex-col gap-1.5 relative border ${
                  isActive
                    ? 'bg-gradient-to-r from-indigo-600 to-blue-600 text-white border-indigo-400/50 shadow-lg shadow-indigo-500/25 ring-1 ring-indigo-400/30'
                    : 'bg-slate-950/40 hover:bg-slate-800/80 text-slate-300 border-slate-800/60 hover:border-slate-700'
                }`}
              >
                {/* Top Row: Index Badge & Chapter Title */}
                <div className="flex items-center gap-2 w-full min-w-0">
                  <span className={`text-[10px] font-extrabold px-1.5 py-0.5 rounded-md flex-shrink-0 font-mono ${
                    isActive 
                      ? 'bg-white/20 text-white' 
                      : 'bg-slate-800 text-slate-400 group-hover:bg-slate-700 group-hover:text-slate-200'
                  }`}>
                    #{chap.index + 1}
                  </span>

                  <span className={`text-xs font-semibold truncate flex-1 ${
                    isActive ? 'text-white font-bold' : 'text-slate-200 group-hover:text-white'
                  }`}>
                    {chap.title}
                  </span>

                  <ChevronRight className={`w-3.5 h-3.5 flex-shrink-0 transition-all ${
                    isActive ? 'text-white opacity-100 translate-x-0' : 'text-slate-500 opacity-0 -translate-x-1 group-hover:opacity-100 group-hover:translate-x-0'
                  }`} />
                </div>

                {/* Bottom Row: Stats & Status */}
                <div className="flex items-center justify-between text-[10px] text-slate-400 w-full pl-7">
                  <span className={isActive ? 'text-indigo-100' : 'text-slate-400'}>
                    {chap.word_count ? `${chap.word_count.toLocaleString()} từ` : '—'}
                  </span>
                  
                  {isActive && (
                    <span className="inline-flex items-center gap-1 text-[10px] font-bold text-white bg-white/20 px-1.5 py-0.2 rounded">
                      <BookOpen className="w-2.5 h-2.5" /> Đang đọc
                    </span>
                  )}
                </div>
              </button>
            );
          })}

          {filtered.length === 0 && (
            <div className="p-8 text-center text-slate-500 text-xs flex flex-col items-center gap-2">
              <BookOpen className="w-8 h-8 opacity-30 stroke-1" />
              <span>Không tìm thấy chương nào trùng khớp</span>
            </div>
          )}
        </div>
      </aside>
    </div>
  );
}
