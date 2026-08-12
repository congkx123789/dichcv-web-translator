import React from 'react';
import { BookOpen, Download, Upload, RotateCcw } from 'lucide-react';

export default function Header({ activeTab, setActiveTab, hasNovel, onResetNovel }) {
  return (
    <header className="h-16 bg-slate-900/50 backdrop-blur-md border-b border-slate-800 sticky top-0 z-50">
      <div className="container mx-auto px-4 h-full flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
            <BookOpen className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-xl font-bold tracking-tight bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
            Alida TSL Reader
          </h1>
        </div>

        {hasNovel && (
          <nav className="flex items-center p-1 bg-slate-800/50 rounded-xl border border-slate-700/50">
            <button
              onClick={() => setActiveTab('reader')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                activeTab === 'reader'
                  ? 'bg-blue-500/10 text-blue-400 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700/50'
              }`}
            >
              <BookOpen className="w-4 h-4" />
              Trình Đọc
            </button>
            <button
              onClick={() => setActiveTab('converter')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                activeTab === 'converter'
                  ? 'bg-indigo-500/10 text-indigo-400 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700/50'
              }`}
            >
              <Download className="w-4 h-4" />
              Xuất File
            </button>
          </nav>
        )}

        <div className="flex items-center gap-2">
          {hasNovel && (
            <button
              onClick={onResetNovel}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300 hover:text-white border border-slate-700 transition-all"
              title="Xóa cache và tải file truyện khác"
            >
              <Upload className="w-3.5 h-3.5" />
              <span>Tải Truyện Mới</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
