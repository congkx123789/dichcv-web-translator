import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Sparkles, SplitSquareHorizontal, ChevronLeft, ChevronRight, Loader2, Menu, Sliders, Sun, Moon, Coffee, BookOpen, X, Type, ChevronsUp, ChevronsDown, RefreshCw, Zap, ArrowUpToLine, ArrowDownToLine, Home } from 'lucide-react';
import TOCViewer from './TOCViewer';
import { api } from '../utils/api';
import { saveReadingSession } from '../utils/storage';

export default function Reader({ novelData, setNovelData, initialSession }) {
  const [currentIdx, setCurrentIdx] = useState(initialSession?.currentIdx || 0);
  const [translatedCache, setTranslatedCache] = useState(initialSession?.translatedCache || {});
  const [isBilingual, setIsBilingual] = useState(false);
  const [isTranslating, setIsTranslating] = useState(false);
  
  // UI Modal & Drawer States
  const [isTocOpen, setIsTocOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  // Custom Reader Preferences
  const [fontSize, setFontSize] = useState(initialSession?.settings?.fontSize || 18);
  const [fontFamily, setFontFamily] = useState(initialSession?.settings?.fontFamily || 'serif');
  const [theme, setTheme] = useState(initialSession?.settings?.theme || 'dark');
  const [isAutoTranslate, setIsAutoTranslate] = useState(initialSession?.settings?.isAutoTranslate ?? false);

  const viewportRef = useRef(null);
  const topRef = useRef(null);
  const endRef = useRef(null);

  // Race condition guards: track in-flight translation and abort controller
  const abortControllerRef = useRef(null);
  const translatingIdxRef = useRef(null);
  // Debounce ref for chapter navigation
  const navDebounceRef = useRef(null);

  const chapters = novelData.chapters || [];
  const chapter = chapters[currentIdx] || { title: '', content: [] };
  const translated = translatedCache[currentIdx];

  // Auto-save reading session to IndexedDB (F5 survival)
  useEffect(() => {
    if (novelData) {
      saveReadingSession({
        novelData,
        currentIdx,
        translatedCache,
        settings: { fontSize, fontFamily, theme, isAutoTranslate }
      });
    }
  }, [novelData, currentIdx, translatedCache, fontSize, fontFamily, theme, isAutoTranslate]);

  // Robust, Race-condition-safe Chapter Translation Function
  const translateChapterByIdx = useCallback(async (targetIdx, force = false) => {
    const targetChap = chapters[targetIdx];
    if (!targetChap || !targetChap.content || targetChap.content.length === 0) return;

    // Use functional updater to get latest cache without stale closure
    const cacheSnapshot = await new Promise(resolve => {
      setTranslatedCache(prev => { resolve(prev); return prev; });
    });
    if (cacheSnapshot[targetIdx] && !force) return;

    // If already translating this exact index, skip
    if (translatingIdxRef.current === targetIdx && !force) return;

    // Abort any previous in-flight translation
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;
    translatingIdxRef.current = targetIdx;

    setIsTranslating(true);
    try {
      const res = await api.translateChapter(targetChap.title, targetChap.content, controller.signal);
      // Only update if this is still the active request
      if (!controller.signal.aborted) {
        setTranslatedCache(prev => ({ ...prev, [targetIdx]: res }));
      }
    } catch (e) {
      if (e.name !== 'AbortError' && !controller.signal.aborted) {
        console.error('Translation error:', e.message);
      }
    } finally {
      if (translatingIdxRef.current === targetIdx) {
        setIsTranslating(false);
        translatingIdxRef.current = null;
        abortControllerRef.current = null;
      }
    }
  }, [chapters]);

  // Debounced chapter navigation to prevent rapid-click race conditions
  const navigateToIdx = useCallback((newIdx) => {
    if (navDebounceRef.current) clearTimeout(navDebounceRef.current);
    navDebounceRef.current = setTimeout(() => {
      setCurrentIdx(newIdx);
    }, 80);
  }, []);

  const goToPrev = useCallback(() => {
    setCurrentIdx(prev => {
      const next = Math.max(0, prev - 1);
      return next;
    });
  }, []);

  const goToNext = useCallback(() => {
    setCurrentIdx(prev => {
      const next = Math.min(chapters.length - 1, prev + 1);
      return next;
    });
  }, [chapters.length]);

  // Cleanup abort on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) abortControllerRef.current.abort();
      if (navDebounceRef.current) clearTimeout(navDebounceRef.current);
    };
  }, []);

  // Auto-Translate when changing chapters if Auto-Translate Mode is ON
  useEffect(() => {
    if (isAutoTranslate && chapter && chapter.content?.length > 0) {
      // Delay slightly to let navigation debounce settle before firing API
      const timer = setTimeout(() => {
        setTranslatedCache(prev => {
          if (!prev[currentIdx]) {
            translateChapterByIdx(currentIdx, false);
          }
          return prev;
        });
      }, 150);
      return () => clearTimeout(timer);
    }
  }, [currentIdx, isAutoTranslate, translateChapterByIdx]);

  // Scroll to top on chapter change instantly
  useEffect(() => {
    if (viewportRef.current) {
      viewportRef.current.scrollTop = 0;
    }
    if (topRef.current) {
      topRef.current.scrollIntoView({ behavior: 'auto', block: 'start' });
    }
    window.scrollTo({ top: 0, behavior: 'auto' });
  }, [currentIdx]);

  // Keyboard navigation (ArrowLeft / ArrowRight / Home / End)
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') return;
      if (e.key === 'ArrowLeft') {
        goToPrev();
      } else if (e.key === 'ArrowRight') {
        goToNext();
      } else if (e.key === 'Home') {
        scrollToHome();
      } else if (e.key === 'End') {
        scrollToEnd();
      } else if (e.key === 'Escape') {
        setIsTocOpen(false);
        setIsSettingsOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [goToPrev, goToNext]);

  // Scroll Actions
  const scrollToHome = () => {
    if (viewportRef.current) {
      viewportRef.current.scrollTop = 0;
      viewportRef.current.scrollTo({ top: 0, behavior: 'smooth' });
    }
    if (topRef.current) {
      topRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const scrollToEnd = () => {
    if (viewportRef.current) {
      viewportRef.current.scrollTo({ 
        top: viewportRef.current.scrollHeight, 
        behavior: 'smooth' 
      });
    }
    if (endRef.current) {
      endRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
  };

  // Theme Styles Configuration
  const themeStyles = {
    light: {
      bg: 'bg-white text-slate-800 border-slate-200',
      header: 'bg-white/90 border-slate-200 text-slate-800',
      bottomBar: 'bg-white/95 border-slate-200 text-slate-800 shadow-slate-200/50',
      dropdown: 'bg-slate-100 border-slate-300 text-slate-800',
      card: 'bg-slate-50 border-slate-200 text-slate-800 hover:bg-slate-100',
    },
    sepia: {
      bg: 'bg-[#fbf0d9] text-[#433422] border-[#e8d7b8]',
      header: 'bg-[#fbf0d9]/90 border-[#e8d7b8] text-[#433422]',
      bottomBar: 'bg-[#f8e7c5]/95 border-[#e2cfab] text-[#433422] shadow-[#e8d7b8]/50',
      dropdown: 'bg-[#f4e4c3] border-[#dfcb9f] text-[#433422]',
      card: 'bg-[#f4e4c3]/60 border-[#e5d2aa] text-[#433422] hover:bg-[#eee0bd]',
    },
    dark: {
      bg: 'bg-slate-900 text-slate-100 border-slate-800',
      header: 'bg-slate-950/85 border-slate-800/80 text-slate-100',
      bottomBar: 'bg-slate-950/95 border-slate-800/80 text-slate-100 shadow-black/40',
      dropdown: 'bg-slate-900 border-slate-700 text-slate-200',
      card: 'bg-slate-800/40 border-slate-800 text-slate-200 hover:bg-slate-800',
    },
    onyx: {
      bg: 'bg-black text-zinc-200 border-zinc-900',
      header: 'bg-zinc-950/90 border-zinc-900 text-zinc-100',
      bottomBar: 'bg-zinc-950/95 border-zinc-900 text-zinc-100 shadow-black/80',
      dropdown: 'bg-zinc-900 border-zinc-800 text-zinc-200',
      card: 'bg-zinc-900/60 border-zinc-800 text-zinc-200 hover:bg-zinc-900',
    }
  };

  const fontClass = {
    serif: 'font-serif',
    sans: 'font-sans',
    mono: 'font-mono'
  }[fontFamily];

  const currentTheme = themeStyles[theme];

  return (
    <div className={`relative flex flex-col h-full w-full min-h-0 overflow-hidden transition-colors duration-300 ${currentTheme.bg}`}>
      
      {/* Off-canvas TOC Drawer */}
      <TOCViewer 
        novelData={novelData} 
        setNovelData={setNovelData} 
        currentChapter={currentIdx} 
        setCurrentChapter={setCurrentIdx} 
        isOpen={isTocOpen}
        onClose={() => setIsTocOpen(false)}
      />

      {/* Top Header Reading Toolbar */}
      <header className={`h-14 md:h-16 border-b backdrop-blur-md flex items-center justify-between px-3 sm:px-6 z-20 sticky top-0 gap-2 transition-colors ${currentTheme.header}`}>
        
        {/* Left: Menu Hamburger & Quick Info */}
        <div className="flex items-center gap-2 min-w-0 flex-1">
          <button
            onClick={() => setIsTocOpen(true)}
            className="p-2 rounded-xl bg-indigo-600/10 hover:bg-indigo-600/20 text-indigo-400 border border-indigo-500/20 transition-all flex items-center gap-1.5 text-xs font-semibold flex-shrink-0"
            title="Mở Mục Lục Truyện"
          >
            <Menu className="w-4 h-4" />
            <span className="hidden sm:inline">Mục Lục</span>
          </button>

          <div className="min-w-0 flex-1 pl-1">
            <h2 className="text-xs sm:text-sm font-bold truncate" title={chapter.title}>
              {chapter.title || 'Đang tải...'}
            </h2>
            <p className="text-[10px] sm:text-xs text-slate-400 truncate hidden xs:block" title={novelData.metadata.title}>
              {novelData.metadata.title}
            </p>
          </div>
        </div>

        {/* Right: Actions & Settings */}
        <div className="flex items-center gap-1.5 sm:gap-2 flex-shrink-0">
          
          {/* Quick Home Button */}
          <button
            onClick={scrollToHome}
            className="p-2 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-indigo-400 hover:text-white transition-all border border-slate-700/60"
            title="Đầu trang (Home)"
          >
            <ChevronsUp className="w-4 h-4" />
          </button>

          {/* Quick End Button */}
          <button
            onClick={scrollToEnd}
            className="p-2 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-indigo-400 hover:text-white transition-all border border-slate-700/60"
            title="Cuối trang (End)"
          >
            <ChevronsDown className="w-4 h-4" />
          </button>

          {/* Auto Translate Toggle Switch */}
          <button
            onClick={() => setIsAutoTranslate(!isAutoTranslate)}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-xs font-semibold transition-all border ${
              isAutoTranslate
                ? 'bg-amber-500/20 text-amber-300 border-amber-500/40 shadow-sm'
                : 'bg-slate-800/80 text-slate-400 hover:text-slate-200 border-slate-700'
            }`}
            title="Tự động dịch sang Tiếng Việt khi chuyển chương"
          >
            <Zap className={`w-3.5 h-3.5 ${isAutoTranslate ? 'fill-amber-400 text-amber-400' : ''}`} />
            <span className="hidden md:inline">{isAutoTranslate ? 'Auto Dịch: BẬT' : 'Auto Dịch: TẮT'}</span>
          </button>

          {/* AI Translate Chapter Button */}
          <button
            onClick={() => translateChapterByIdx(currentIdx, false)}
            disabled={isTranslating}
            className={`flex items-center gap-1.5 px-2.5 sm:px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all shadow-sm ${
              translated 
                ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30' 
                : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-indigo-500/20'
            }`}
          >
            {isTranslating ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Sparkles className="w-3.5 h-3.5" />
            )}
            <span className="hidden xs:inline">{translated ? 'Đã Dịch Chương Này' : 'Dịch Chương Này'}</span>
          </button>

          {/* Bilingual Toggle Button */}
          {translated && (
            <button
              onClick={() => setIsBilingual(!isBilingual)}
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-xs font-semibold transition-all border ${
                isBilingual 
                  ? 'bg-blue-500/20 text-blue-300 border-blue-500/40' 
                  : 'bg-slate-800/80 text-slate-300 hover:bg-slate-700 border-slate-700'
              }`}
              title="Chuyển chế độ xem Song Ngữ Trung-Việt"
            >
              <SplitSquareHorizontal className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Song Ngữ</span>
            </button>
          )}

          {/* Reading Settings Button */}
          <button
            onClick={() => setIsSettingsOpen(true)}
            className="p-2 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white transition-all border border-slate-700/60"
            title="Tùy chỉnh Cỡ chữ & Màu nền"
          >
            <Sliders className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* Reading Customization Settings Popover/Modal */}
      {isSettingsOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setIsSettingsOpen(false)} />
          
          <div className="relative w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl p-5 z-10 space-y-5 animate-scale-up text-slate-100">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2 font-bold text-sm">
                <Sliders className="w-4 h-4 text-indigo-400" />
                <span>Tùy Chỉnh Giao Diện Đọc</span>
              </div>
              <button 
                onClick={() => setIsSettingsOpen(false)}
                className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Quick Scroll Home / End Buttons */}
            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Cuộn Nhanh Trang</label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => { scrollToHome(); setIsSettingsOpen(false); }}
                  className="flex items-center justify-center gap-2 py-2 px-3 rounded-xl bg-slate-950 border border-slate-800 text-xs font-semibold text-indigo-300 hover:bg-slate-800 transition-colors"
                >
                  <Home className="w-4 h-4" />
                  <span>Về Đầu Trang (Home)</span>
                </button>

                <button
                  onClick={() => { scrollToEnd(); setIsSettingsOpen(false); }}
                  className="flex items-center justify-center gap-2 py-2 px-3 rounded-xl bg-slate-950 border border-slate-800 text-xs font-semibold text-indigo-300 hover:bg-slate-800 transition-colors"
                >
                  <ArrowDownToLine className="w-4 h-4" />
                  <span>Xuống Cuối Trang (End)</span>
                </button>
              </div>
            </div>

            {/* Auto Translate Toggle Row */}
            <div className="flex items-center justify-between p-3 rounded-xl bg-slate-950/60 border border-slate-800">
              <div className="flex items-center gap-2">
                <Zap className={`w-4 h-4 ${isAutoTranslate ? 'text-amber-400 fill-amber-400' : 'text-slate-400'}`} />
                <div>
                  <div className="text-xs font-bold">Tự Động Dịch Khi Chuyển Chương</div>
                  <div className="text-[10px] text-slate-400">Tự động dịch sang Tiếng Việt mỗi khi bấm Next chương</div>
                </div>
              </div>
              <button
                onClick={() => setIsAutoTranslate(!isAutoTranslate)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  isAutoTranslate ? 'bg-amber-500' : 'bg-slate-700'
                }`}
              >
                <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  isAutoTranslate ? 'translate-x-6' : 'translate-x-1'
                }`} />
              </button>
            </div>

            {/* Theme Presets */}
            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Màu Nền Đọc</label>
              <div className="grid grid-cols-4 gap-2">
                <button
                  onClick={() => setTheme('light')}
                  className={`flex flex-col items-center gap-1.5 p-2.5 rounded-xl border text-xs font-medium transition-all ${
                    theme === 'light' ? 'ring-2 ring-indigo-500 border-indigo-500 font-bold' : 'border-slate-700 hover:border-slate-600'
                  } bg-white text-slate-900`}
                >
                  <Sun className="w-4 h-4" />
                  <span>Sáng</span>
                </button>

                <button
                  onClick={() => setTheme('sepia')}
                  className={`flex flex-col items-center gap-1.5 p-2.5 rounded-xl border text-xs font-medium transition-all ${
                    theme === 'sepia' ? 'ring-2 ring-indigo-500 border-indigo-500 font-bold' : 'border-[#e0d0b0] hover:border-[#cbba96]'
                  } bg-[#fbf0d9] text-[#433422]`}
                >
                  <Coffee className="w-4 h-4" />
                  <span>Sepia</span>
                </button>

                <button
                  onClick={() => setTheme('dark')}
                  className={`flex flex-col items-center gap-1.5 p-2.5 rounded-xl border text-xs font-medium transition-all ${
                    theme === 'dark' ? 'ring-2 ring-indigo-500 border-indigo-500 font-bold' : 'border-slate-700 hover:border-slate-600'
                  } bg-slate-900 text-slate-100`}
                >
                  <Moon className="w-4 h-4" />
                  <span>Tối</span>
                </button>

                <button
                  onClick={() => setTheme('onyx')}
                  className={`flex flex-col items-center gap-1.5 p-2.5 rounded-xl border text-xs font-medium transition-all ${
                    theme === 'onyx' ? 'ring-2 ring-indigo-500 border-indigo-500 font-bold' : 'border-zinc-800 hover:border-zinc-700'
                  } bg-black text-zinc-200`}
                >
                  <BookOpen className="w-4 h-4" />
                  <span>Đêm</span>
                </button>
              </div>
            </div>

            {/* Font Family Selector */}
            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Phông Chữ</label>
              <div className="grid grid-cols-3 gap-2">
                <button
                  onClick={() => setFontFamily('serif')}
                  className={`py-2 px-3 rounded-xl border text-xs font-serif transition-all ${
                    fontFamily === 'serif' ? 'bg-indigo-600 text-white border-indigo-500 font-bold' : 'bg-slate-950 border-slate-800 text-slate-300 hover:bg-slate-800'
                  }`}
                >
                  Cổ Điển (Serif)
                </button>

                <button
                  onClick={() => setFontFamily('sans')}
                  className={`py-2 px-3 rounded-xl border text-xs font-sans transition-all ${
                    fontFamily === 'sans' ? 'bg-indigo-600 text-white border-indigo-500 font-bold' : 'bg-slate-950 border-slate-800 text-slate-300 hover:bg-slate-800'
                  }`}
                >
                  Hiện Đại (Sans)
                </button>

                <button
                  onClick={() => setFontFamily('mono')}
                  className={`py-2 px-3 rounded-xl border text-xs font-mono transition-all ${
                    fontFamily === 'mono' ? 'bg-indigo-600 text-white border-indigo-500 font-bold' : 'bg-slate-950 border-slate-800 text-slate-300 hover:bg-slate-800'
                  }`}
                >
                  Mã Máy (Mono)
                </button>
              </div>
            </div>

            {/* Font Size Slider */}
            <div className="space-y-2">
              <div className="flex justify-between items-center text-xs font-semibold">
                <span className="text-slate-400 uppercase tracking-wider">Cỡ Chữ</span>
                <span className="font-mono text-indigo-400 font-bold">{fontSize}px</span>
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setFontSize(prev => Math.max(14, prev - 2))}
                  className="px-3 py-1.5 rounded-xl bg-slate-950 border border-slate-800 hover:bg-slate-800 font-bold text-sm"
                >
                  A-
                </button>
                
                <input
                  type="range"
                  min="14"
                  max="28"
                  step="2"
                  value={fontSize}
                  onChange={(e) => setFontSize(Number(e.target.value))}
                  className="flex-1 accent-indigo-500 cursor-pointer"
                />

                <button
                  onClick={() => setFontSize(prev => Math.min(28, prev + 2))}
                  className="px-3 py-1.5 rounded-xl bg-slate-950 border border-slate-800 hover:bg-slate-800 font-bold text-sm"
                >
                  A+
                </button>
              </div>
            </div>

          </div>
        </div>
      )}

      {/* Floating Side Action Dock (Thanh công cụ nổi góc hông phải) */}
      <div className="fixed right-3 sm:right-6 bottom-20 z-40 flex flex-col gap-2 animate-fade-in">
        <div className="bg-slate-950/90 border border-slate-800 shadow-2xl backdrop-blur-md rounded-2xl p-1.5 flex flex-col gap-1.5 text-slate-300">
          
          {/* Scroll to Top (Home) */}
          <button
            onClick={scrollToHome}
            className="p-2.5 rounded-xl hover:bg-slate-800 hover:text-white transition-all group relative"
            title="Đầu trang (Home)"
          >
            <Home className="w-4 h-4 text-indigo-400 group-hover:scale-110 transition-transform" />
          </button>

          {/* Quick TOC Drawer Toggle */}
          <button
            onClick={() => setIsTocOpen(true)}
            className="p-2.5 rounded-xl hover:bg-slate-800 hover:text-white transition-all group relative"
            title="Mở Mục Lục"
          >
            <Menu className="w-4 h-4 text-blue-400 group-hover:scale-110 transition-transform" />
          </button>

          {/* Quick AI Translate Button */}
          <button
            onClick={() => translateChapterByIdx(currentIdx, true)}
            disabled={isTranslating}
            className={`p-2.5 rounded-xl transition-all group relative ${
              translated 
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 hover:bg-emerald-500/30' 
                : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-500/30'
            }`}
            title={translated ? "Bấm để dịch lại chương này" : "Bấm để dịch AI chương này"}
          >
            {isTranslating ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : translated ? (
              <RefreshCw className="w-4 h-4 text-emerald-300 group-hover:rotate-180 transition-transform duration-500" />
            ) : (
              <Sparkles className="w-4 h-4 text-white group-hover:scale-110 transition-transform" />
            )}
          </button>

          {/* Quick Settings Toggle */}
          <button
            onClick={() => setIsSettingsOpen(true)}
            className="p-2.5 rounded-xl hover:bg-slate-800 hover:text-white transition-all group relative"
            title="Tùy chọn Cỡ chữ & Nền"
          >
            <Sliders className="w-4 h-4 text-slate-300 group-hover:scale-110 transition-transform" />
          </button>

          {/* Scroll to Bottom (End) */}
          <button
            onClick={scrollToEnd}
            className="p-2.5 rounded-xl hover:bg-slate-800 hover:text-white transition-all group relative"
            title="Cuối trang (End)"
          >
            <ArrowDownToLine className="w-4 h-4 text-indigo-400 group-hover:scale-110 transition-transform" />
          </button>
        </div>
      </div>

      {/* Floating Side Margin Flappers (Nút chuyển chương nổi hai bên lề) */}
      <button
        onClick={goToPrev}
        disabled={currentIdx === 0}
        className="fixed left-2 sm:left-4 top-1/2 -translate-y-1/2 z-30 p-2.5 sm:p-3.5 rounded-full bg-slate-950/80 hover:bg-indigo-600 border border-slate-800 text-slate-300 hover:text-white shadow-2xl backdrop-blur-md transition-all duration-300 opacity-40 hover:opacity-100 disabled:opacity-0 active:scale-90"
        title="Chương trước (←)"
      >
        <ChevronLeft className="w-5 h-5 sm:w-6 sm:h-6" />
      </button>

      <button
        onClick={goToNext}
        disabled={currentIdx === chapters.length - 1}
        className="fixed right-16 sm:right-20 top-1/2 -translate-y-1/2 z-30 p-2.5 sm:p-3.5 rounded-full bg-slate-950/80 hover:bg-indigo-600 border border-slate-800 text-slate-300 hover:text-white shadow-2xl backdrop-blur-md transition-all duration-300 opacity-40 hover:opacity-100 disabled:opacity-0 active:scale-90"
        title="Chương sau (→)"
      >
        <ChevronRight className="w-5 h-5 sm:w-6 sm:h-6" />
      </button>

      {/* Main Novel Viewport */}
      <main 
        ref={viewportRef} 
        className="flex-1 overflow-y-auto px-4 sm:px-8 md:px-16 lg:px-24 py-8 scroll-smooth custom-scrollbar pb-32"
      >
        <div className="max-w-3xl mx-auto">
          
          {/* Chapter Header */}
          <div ref={topRef} className="mb-8 pb-6 border-b border-current/15">
            <div className="flex items-center gap-2 mb-3 flex-wrap">
              <span className="text-xs font-extrabold uppercase tracking-wider px-2.5 py-1 rounded-md bg-indigo-500/10 text-indigo-500 border border-indigo-500/20 font-mono">
                Chương {currentIdx + 1} / {chapters.length}
              </span>
              
              {translated && (
                <span className="text-xs font-semibold text-emerald-600 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                  ✓ Đã dịch Tiếng Việt
                </span>
              )}
            </div>

            <h1 className={`text-2xl sm:text-3xl md:text-4xl font-bold leading-snug tracking-tight ${fontClass}`}>
              {isBilingual && translated ? `${chapter.title} / ${translated.title}` : (translated?.title || chapter.title)}
            </h1>
          </div>
          
          {/* Novel Text Paragraphs */}
          <div 
            className={`space-y-6 leading-relaxed transition-all ${fontClass}`}
            style={{ fontSize: `${fontSize}px` }}
          >
            {isBilingual && translated ? (
              chapter.content.map((line, i) => line.trim() && (
                <div key={i} className={`group flex flex-col gap-1.5 p-4 rounded-xl transition-colors border border-transparent ${currentTheme.card}`}>
                  <p className="opacity-60 text-sm font-sans">{line}</p>
                  <p className="font-serif leading-relaxed">{translated.content[i]}</p>
                </div>
              ))
            ) : (
              (translated || chapter).content.map((line, i) => line.trim() && (
                <p key={i} className="mb-5 leading-relaxed tracking-normal">
                  {line}
                </p>
              ))
            )}
          </div>

          {/* End of Chapter Spacer */}
          <div ref={endRef} className="mt-16 text-center text-xs opacity-40 font-mono pb-8">
            — Hết Chương {currentIdx + 1} —
          </div>

        </div>
      </main>

      {/* Sticky Bottom Chapter Navigation Controls (Fixed Bar) */}
      <footer className={`fixed bottom-0 inset-x-0 z-30 h-16 border-t backdrop-blur-lg flex items-center justify-between px-3 sm:px-8 gap-2 transition-colors shadow-2xl ${currentTheme.bottomBar}`}>
        
        {/* Prev Chapter Button */}
        <button
          onClick={goToPrev}
          disabled={currentIdx === 0}
          className="flex items-center gap-1.5 px-3 sm:px-5 py-2.5 rounded-xl text-xs sm:text-sm font-bold transition-all disabled:opacity-30 disabled:cursor-not-allowed bg-indigo-600/10 hover:bg-indigo-600/20 text-indigo-400 border border-indigo-500/20 active:scale-95 flex-shrink-0"
        >
          <ChevronLeft className="w-4 h-4" />
          <span>⬅️ Chương Trước</span>
        </button>

        {/* Home & End Action Buttons & Chapter Quick Select */}
        <div className="flex items-center gap-1.5 min-w-0 max-w-[240px] sm:max-w-[380px]">
          <button
            onClick={scrollToHome}
            className="p-2 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-indigo-400 transition-colors flex-shrink-0"
            title="Đầu trang (Home)"
          >
            <Home className="w-4 h-4" />
          </button>

          <select
            value={currentIdx}
            onChange={(e) => navigateToIdx(Number(e.target.value))}
            className={`w-full text-xs font-semibold rounded-xl px-2 py-2 truncate focus:outline-none border cursor-pointer ${currentTheme.dropdown}`}
          >
            {chapters.map((c, idx) => (
              <option key={idx} value={idx}>
                Chương {idx + 1}: {c.title}
              </option>
            ))}
          </select>

          <button
            onClick={scrollToEnd}
            className="p-2 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-indigo-400 transition-colors flex-shrink-0"
            title="Cuối trang (End)"
          >
            <ArrowDownToLine className="w-4 h-4" />
          </button>
        </div>

        {/* Next Chapter Button */}
        <button
          onClick={goToNext}
          disabled={currentIdx === chapters.length - 1}
          className="flex items-center gap-1.5 px-3 sm:px-5 py-2.5 rounded-xl text-xs sm:text-sm font-bold transition-all disabled:opacity-30 disabled:cursor-not-allowed bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-500 hover:to-blue-500 text-white shadow-lg shadow-indigo-500/20 border border-indigo-400/30 active:scale-95 flex-shrink-0"
        >
          <span>Chương Sau ➡️</span>
          <ChevronRight className="w-4 h-4" />
        </button>
      </footer>

    </div>
  );
}
