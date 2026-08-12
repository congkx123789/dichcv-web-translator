// Browser Storage Manager for Alida Web Novel Reader (IndexedDB & LocalStorage)
const DB_NAME = 'AlidaNovelReaderDB';
const DB_VERSION = 1;
const STORE_NAME = 'reading_session';

function openDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = (e) => {
      const db = e.target.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME);
      }
    };
    request.onsuccess = (e) => resolve(e.target.result);
    request.onerror = (e) => reject(e.target.error);
  });
}

export async function saveReadingSession(sessionData) {
  try {
    const db = await openDB();
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    store.put(sessionData, 'current_session');
    return new Promise((resolve) => {
      tx.oncomplete = () => resolve(true);
    });
  } catch (err) {
    console.warn("⚠️ Failed to save session to IndexedDB:", err);
  }
}

export async function loadReadingSession() {
  try {
    const db = await openDB();
    const tx = db.transaction(STORE_NAME, 'readonly');
    const store = tx.objectStore(STORE_NAME);
    const request = store.get('current_session');
    return new Promise((resolve) => {
      request.onsuccess = () => resolve(request.result || null);
      request.onerror = () => resolve(null);
    });
  } catch (err) {
    console.warn("⚠️ Failed to load session from IndexedDB:", err);
    return null;
  }
}

export async function clearReadingSession() {
  try {
    const db = await openDB();
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    store.delete('current_session');
    localStorage.removeItem('alida_session_meta');
  } catch (err) {
    console.warn("⚠️ Failed to clear session:", err);
  }
}
