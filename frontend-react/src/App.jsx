import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import Uploader from './components/Uploader';
import Reader from './components/Reader';
import Exporter from './components/Exporter';
import { loadReadingSession, clearReadingSession } from './utils/storage';

function App() {
  const [novelData, setNovelData] = useState(null);
  const [initialSession, setInitialSession] = useState(null);
  const [activeTab, setActiveTab] = useState('reader'); // 'reader' or 'converter'
  const [isStorageLoaded, setIsStorageLoaded] = useState(false);

  // Restore session from IndexedDB on startup (F5 survival)
  useEffect(() => {
    loadReadingSession().then((session) => {
      if (session && session.novelData) {
        setNovelData(session.novelData);
        setInitialSession(session);
      }
      setIsStorageLoaded(true);
    });
  }, []);

  const handleResetNovel = async () => {
    if (window.confirm("Bạn có chắc chắn muốn tải truyện mới? Tiến trình đọc hiện tại sẽ bị xóa khỏi cache.")) {
      await clearReadingSession();
      setNovelData(null);
      setInitialSession(null);
    }
  };

  if (!isStorageLoaded) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-200 flex items-center justify-center">
        <div className="animate-pulse text-indigo-400 font-medium">Đang tải bộ nhớ đọc...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 font-sans flex flex-col">
      <Header 
        activeTab={activeTab} 
        setActiveTab={setActiveTab} 
        hasNovel={Boolean(novelData)} 
        onResetNovel={handleResetNovel}
      />
      
      <main className="flex-1 container mx-auto px-4 py-6 flex flex-col h-[calc(100vh-64px)] overflow-hidden">
        {!novelData ? (
          <div className="flex-1 flex flex-col items-center justify-center space-y-8 h-full overflow-y-auto">
            <div className="text-center space-y-4 max-w-2xl">
              <h2 className="text-4xl font-bold bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">
                Alida Web Novel Studio
              </h2>
              <p className="text-slate-400 text-lg">
                Hệ thống dịch máy AI siêu tốc với Native C++ ONNX GPU. Hỗ trợ đọc và xuất file mượt mà.
              </p>
            </div>
            <Uploader setNovelData={setNovelData} />
          </div>
        ) : (
          <div className="flex-1 flex gap-6 h-full min-h-0">
            {activeTab === 'reader' ? (
              <Reader 
                novelData={novelData} 
                setNovelData={setNovelData} 
                initialSession={initialSession}
              />
            ) : (
              <Exporter novelData={novelData} setNovelData={setNovelData} />
            )}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
