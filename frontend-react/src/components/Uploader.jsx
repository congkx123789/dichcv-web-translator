import React, { useCallback, useState } from 'react';
import { Upload, FileText, Loader2 } from 'lucide-react';
import { api } from '../utils/api';

export default function Uploader({ setNovelData }) {
  const [isDragging, setIsDragging] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [translateToc, setTranslateToc] = useState(true);
  const [error, setError] = useState('');

  const onDragOver = useCallback((e) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const onDragLeave = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const processFile = async (file) => {
    if (!file) return;
    setIsLoading(true);
    setError('');
    
    try {
      // Pass false to parseNovel so it returns raw chapters instantly without background translation
      const data = await api.parseNovel(file, false);
      setNovelData(data);
    } catch (err) {
      setError(err.message || 'Lỗi khi phân tích file');
    } finally {
      setIsLoading(false);
    }
  };

  const onDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer?.files?.[0];
    if (file) processFile(file);
  }, [translateToc]);

  const onFileInput = (e) => {
    const file = e.target.files?.[0];
    if (file) processFile(file);
  };

  return (
    <div className="w-full max-w-2xl mx-auto space-y-6">
      <div 
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        className={`relative border-2 border-dashed rounded-3xl p-12 text-center transition-all duration-300 ease-out flex flex-col items-center justify-center min-h-[320px] bg-slate-900/40 backdrop-blur-sm
          ${isDragging 
            ? 'border-blue-500 bg-blue-500/10 scale-[1.02] shadow-2xl shadow-blue-500/20' 
            : 'border-slate-700/60 hover:border-blue-400/50 hover:bg-slate-800/60'
          }`}
      >
        <input 
          type="file" 
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
          onChange={onFileInput}
          disabled={isLoading}
          accept=".txt,.zip,.epub"
        />
        
        {isLoading ? (
          <div className="flex flex-col items-center text-blue-400 space-y-4">
            <Loader2 className="w-16 h-16 animate-spin" />
            <p className="text-xl font-medium animate-pulse">Đang phân tích & dịch siêu tốc...</p>
          </div>
        ) : (
          <>
            <div className={`w-20 h-20 rounded-2xl bg-blue-500/10 flex items-center justify-center mb-6 transition-transform duration-300 ${isDragging ? 'scale-110' : ''}`}>
              <Upload className={`w-10 h-10 ${isDragging ? 'text-blue-400' : 'text-blue-500'}`} />
            </div>
            <h3 className="text-2xl font-semibold text-slate-200 mb-3">Tải File Truyện Lên</h3>
            <p className="text-slate-400 max-w-md mb-8 leading-relaxed">
              Kéo thả file <span className="text-blue-400 font-medium">.txt, .zip, .epub</span> vào đây hoặc click để chọn file từ máy tính
            </p>
            
            <div className="relative z-20 flex items-center gap-3 bg-slate-950/50 px-6 py-3 rounded-xl border border-slate-700">
              <div className="relative flex items-center cursor-pointer">
                <input 
                  type="checkbox" 
                  id="toc-trans" 
                  checked={translateToc}
                  onChange={(e) => setTranslateToc(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-slate-700 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-500"></div>
              </div>
              <label htmlFor="toc-trans" className="text-sm text-slate-300 cursor-pointer font-medium select-none">
                Dịch nhanh Tên Truyện & Mục Lục
              </label>
            </div>
          </>
        )}
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-xl text-center flex items-center justify-center gap-2">
          <span className="font-semibold">Lỗi:</span> {error}
        </div>
      )}
    </div>
  );
}
