const API_BASE = import.meta.env.VITE_API_BASE_URL || 
  (window.location.origin.includes('5173') ? 'http://localhost:8000/api' : 'https://dichcv.lyvuha.com/api');



export const api = {
  parseNovel: async (file, translateToc = false) => {
    const formData = new FormData();
    formData.append('file', file);
    if (translateToc) {
      formData.append('translate_toc', 'true');
    }
    const res = await fetch(`${API_BASE}/novel/parse`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  translateToc: async (metadata, chapters) => {
    const res = await fetch(`${API_BASE}/novel/translate_toc`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ metadata, chapters }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  translateTocStream: async function* (metadata, chapters) {
    const res = await fetch(`${API_BASE}/novel/translate_toc_stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ metadata, chapters }),
    });
    if (!res.ok) throw new Error(await res.text());

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop(); // keep the last incomplete line
      
      for (const line of lines) {
        if (line.trim()) {
          yield JSON.parse(line);
        }
      }
    }
    
    if (buffer.trim()) {
      yield JSON.parse(buffer);
    }
  },

  translateChapter: async (title, content, signal = null) => {
    const options = {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, content }),
    };
    if (signal) options.signal = signal;
    const res = await fetch(`${API_BASE}/translate/chapter`, options);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  exportNovel: async (exportData) => {
    const res = await fetch(`${API_BASE}/novel/export`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(exportData),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.blob();
  },
  
  translateFile: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/translate/file`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) throw new Error(await res.text());
    return res.blob();
  }
};
