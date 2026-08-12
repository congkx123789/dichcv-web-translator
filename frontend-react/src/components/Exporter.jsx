import React, { useState } from 'react';
import { Download, Book, FileText, FileCode2, Loader2, Info } from 'lucide-react';
import { api } from '../utils/api';

export default function Exporter({ novelData, setNovelData }) {
  const [meta, setMeta] = useState({
    title: novelData.metadata.title || '',
    author: novelData.metadata.author || '',
    description: novelData.metadata.description || '',
  });
  const [isExporting, setIsExporting] = useState(false);
  
  const handleExport = async (format) => {
    setIsExporting(format);
    try {
      const exportData = {
        title: meta.title,
        author: meta.author,
        description: meta.description,
        format: format,
        chapters: novelData.chapters
      };
      
      const blob = await api.exportNovel(exportData);
      
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${meta.title}_Vietnamese.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (e) {
      alert("Lỗi xuất file: " + e.message);
    } finally {
      setIsExporting(false);
    }
  };

  const btnClass = (format, colorClass) => `
    flex flex-col items-center justify-center gap-3 p-6 rounded-2xl border transition-all
    ${isExporting === format ? 'opacity-50 cursor-not-allowed scale-95' : 'hover:-translate-y-1 hover:shadow-xl cursor-pointer'}
    ${colorClass}
  `;

  return (
    <div className="w-full max-w-4xl mx-auto flex gap-8">
      {/* Metadata Editor */}
      <div className="flex-1 bg-slate-900 rounded-3xl border border-slate-800 p-8 shadow-xl">
        <div className="flex items-center gap-3 mb-8 pb-4 border-b border-slate-800">
          <Info className="w-6 h-6 text-blue-400" />
          <h2 className="text-2xl font-bold text-slate-100">Thông Tin Tác Phẩm</h2>
        </div>
        
        <div className="space-y-6">
          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-400">Tên Truyện</label>
            <input 
              type="text" 
              value={meta.title}
              onChange={e => setMeta({...meta, title: e.target.value})}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-slate-200 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/50 transition-all"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-400">Tác Giả</label>
            <input 
              type="text" 
              value={meta.author}
              onChange={e => setMeta({...meta, author: e.target.value})}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-slate-200 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/50 transition-all"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-400">Giới Thiệu (Tóm Tắt)</label>
            <textarea 
              value={meta.description}
              onChange={e => setMeta({...meta, description: e.target.value})}
              rows={6}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-slate-200 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/50 transition-all resize-none"
            />
          </div>
        </div>
      </div>
      
      {/* Export Options */}
      <div className="w-[320px] shrink-0 space-y-4 flex flex-col">
        <h3 className="text-lg font-semibold text-slate-300 mb-2 px-2">Định Dạng Xuất</h3>
        
        <button 
          onClick={() => handleExport('epub')}
          disabled={isExporting}
          className={btnClass('epub', 'bg-blue-500/10 border-blue-500/30 text-blue-400 hover:bg-blue-500/20 hover:border-blue-500/50 shadow-blue-500/10')}
        >
          {isExporting === 'epub' ? <Loader2 className="w-10 h-10 animate-spin" /> : <Book className="w-10 h-10" />}
          <div className="text-center">
            <div className="font-bold text-lg mb-1">Xuất EPUB</div>
            <div className="text-xs opacity-70">Sách điện tử chuẩn, kèm Cover Art</div>
          </div>
        </button>
        
        <button 
          onClick={() => handleExport('html')}
          disabled={isExporting}
          className={btnClass('html', 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20 hover:border-emerald-500/50 shadow-emerald-500/10')}
        >
          {isExporting === 'html' ? <Loader2 className="w-8 h-8 animate-spin" /> : <FileCode2 className="w-8 h-8" />}
          <div className="text-center">
            <div className="font-bold">Xuất HTML</div>
            <div className="text-xs opacity-70">Trang Web Offline</div>
          </div>
        </button>
        
        <button 
          onClick={() => handleExport('txt')}
          disabled={isExporting}
          className={btnClass('txt', 'bg-slate-700/30 border-slate-700 hover:bg-slate-700/50 text-slate-300')}
        >
          {isExporting === 'txt' ? <Loader2 className="w-8 h-8 animate-spin" /> : <FileText className="w-8 h-8" />}
          <div className="text-center">
            <div className="font-bold">Xuất TXT</div>
            <div className="text-xs opacity-70">Văn bản thô, dùng cho TTS</div>
          </div>
        </button>
      </div>
    </div>
  );
}
