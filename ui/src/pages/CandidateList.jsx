import { useState, useEffect, useRef } from 'react';
import { MagnifyingGlass as Search, MapPin, Briefcase, CaretRight as ChevronRight, User, Upload, CheckCircle as CheckCircle2, WarningCircle as AlertCircle, ArrowsClockwise as RefreshCw, DotsThreeVertical as MoreVertical, DownloadSimple as Download, Trash as Trash2, CheckSquare, Square, X, XCircle } from '@phosphor-icons/react';
import { useNavigate, useLocation } from 'react-router-dom';

const AI_NOTES_ENABLED_KEY = 'cip_ai_notes_enabled';

function CandidateList() {
  const navigate = useNavigate();
  const location = useLocation();
  const [candidates, setCandidates] = useState([]);
  const [query, setQuery] = useState('');
  const [city, setCity] = useState('');
  const [title, setTitle] = useState('');
  const [minYoe, setMinYoe] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [openMenuId, setOpenMenuId] = useState(null);
  const [deleteCandidate, setDeleteCandidate] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);
  
  // Search & Warnings State
  const [searchWarnings, setSearchWarnings] = useState([]);
  const [searchProgress, setSearchProgress] = useState(null);
  const [insights, setInsights] = useState({});

  // AI Notes Toggle State
  const [aiNotesEnabled, setAiNotesEnabled] = useState(() => {
    try {
      return window.localStorage.getItem(AI_NOTES_ENABLED_KEY) !== 'false';
    } catch {
      return true;
    }
  });
  const aiNotesEnabledRef = useRef(aiNotesEnabled);
  const insightControllersRef = useRef(new Map());
  const lastSearchedQueryRef = useRef('');
  
  // Upload Manager State
  const [showUploadManager, setShowUploadManager] = useState(false);
  const [uploadQueue, setUploadQueue] = useState([]);

  // Reprocess Manager State
  const [reprocessState, setReprocessState] = useState(null);

  // Multi-Selection State
  const [selectedIds, setSelectedIds] = useState([]);
  const [showBatchDeleteModal, setShowBatchDeleteModal] = useState(false);
  const [isBatchDeleting, setIsBatchDeleting] = useState(false);
  const [listDeleteError, setListDeleteError] = useState(null);
  const [batchDeleteError, setBatchDeleteError] = useState(null);
  const [batchReprocessState, setBatchReprocessState] = useState(null);

  const toggleSelectCandidate = (e, id) => {
    if (e) e.stopPropagation();
    setSelectedIds(prev => 
      prev.includes(id) ? prev.filter(item => item !== id) : [...prev, id]
    );
  };

  const toggleSelectAll = () => {
    if (selectedIds.length === candidates.length && candidates.length > 0) {
      setSelectedIds([]);
    } else {
      setSelectedIds(candidates.map(c => c.id));
    }
  };

  const clearSelection = () => {
    setSelectedIds([]);
  };

  const fireTopInsights = (list, searchQuery) => {
    if (!aiNotesEnabledRef.current || !searchQuery || !searchQuery.trim() || !Array.isArray(list) || list.length === 0) {
      return;
    }
    // Strictly cap to top 3 or whatever smaller count of results exists. NEVER all if list > 3.
    const topCandidates = list.slice(0, Math.min(list.length, 3));
    topCandidates.forEach((c) => {
      if (c && c.id) {
        generateInsight(c.id, searchQuery.trim());
      }
    });
  };

  const toggleAiNotes = () => {
    const next = !aiNotesEnabled;
    aiNotesEnabledRef.current = next;
    setAiNotesEnabled(next);
    try {
      window.localStorage.setItem(AI_NOTES_ENABLED_KEY, String(next));
    } catch {
      // localStorage unavailable; toggle still works for this session
    }

    if (!next) {
      insightControllersRef.current.forEach((controller) => controller.abort());
      insightControllersRef.current.clear();
      setInsights({});
    } else {
      const activeQuery = (query || lastSearchedQueryRef.current || '').trim();
      if (activeQuery) {
        fireTopInsights(candidates, activeQuery);
      }
    }
  };

  const generateInsight = async (candidateId, searchQuery) => {
    if (!aiNotesEnabledRef.current) return;
    const existingController = insightControllersRef.current.get(candidateId);
    if (existingController) existingController.abort();
    const controller = new AbortController();
    insightControllersRef.current.set(candidateId, controller);
    setInsights(prev => ({
      ...prev,
      [candidateId]: { text: '', status: 'loading', controller }
    }));
    
    try {
      const response = await fetch(`/api/candidates/${candidateId}/insight?query=${encodeURIComponent(searchQuery)}`, {
        signal: controller.signal
      });
      if (!response.body) throw new Error('ReadableStream not supported.');

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const block of lines) {
          for (const line of block.split('\n')) {
            if (line.startsWith('data: ')) {
              try {
                const event = JSON.parse(line.substring(6));
                if (event.error) {
                  setInsights(prev => ({
                    ...prev,
                    [candidateId]: {
                      ...prev[candidateId],
                      status: 'error',
                      errorMessage: event.message || 'Generation failed.'
                    }
                  }));
                } else if (event.token && aiNotesEnabledRef.current) {
                  setInsights(prev => ({
                    ...prev,
                    [candidateId]: { 
                      ...prev[candidateId], 
                      text: prev[candidateId].text + event.token 
                    }
                  }));
                }
              } catch (err) {
                console.error('Error parsing insight token:', err);
              }
            }
          }
        }
      }
      if (aiNotesEnabledRef.current) {
        setInsights(prev => ({
          ...prev,
          [candidateId]: { ...prev[candidateId], status: 'done' }
        }));
      }
    } catch (err) {
      if (aiNotesEnabledRef.current) {
        if (err.name === 'AbortError') {
          setInsights(prev => ({
            ...prev,
            [candidateId]: { ...prev[candidateId], status: 'cancelled' }
          }));
        } else {
          console.error('Insight generation failed:', err);
          setInsights(prev => ({
            ...prev,
            [candidateId]: { ...prev[candidateId], status: 'error' }
          }));
        }
      }
    } finally {
      const current = insightControllersRef.current.get(candidateId);
      if (current === controller) {
        insightControllersRef.current.delete(candidateId);
      }
    }
  };

  const handleBatchDownloadResumes = async () => {
    if (!selectedIds.length) return;
    for (let i = 0; i < selectedIds.length; i++) {
      const id = selectedIds[i];
      const link = document.createElement('a');
      link.href = `/api/candidates/${id}/file`;
      link.download = '';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      await new Promise(resolve => setTimeout(resolve, 300));
    }
  };

  const confirmBatchDelete = async () => {
    if (!selectedIds.length) return;
    setIsBatchDeleting(true);
    setBatchDeleteError(null);
    try {
      const res = await fetch('/api/candidates/batch-delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ candidate_ids: selectedIds })
      });
      if (res.ok) {
        setCandidates(prev => prev.filter(c => !selectedIds.includes(c.id)));
        setSelectedIds([]);
        setShowBatchDeleteModal(false);
      } else {
        setBatchDeleteError('Failed to delete selected candidates.');
      }
    } catch (err) {
      console.error('Batch delete failed:', err);
      setBatchDeleteError('An error occurred during batch delete.');
    } finally {
      setIsBatchDeleting(false);
    }
  };

  const handleBatchReprocess = async () => {
    if (!selectedIds.length) return;

    const initialQueue = selectedIds.map(id => {
      const cand = candidates.find(c => c.id === id);
      return {
        candidate_id: id,
        candidate_name: cand ? `${cand.first_name} ${cand.last_name}` : 'Candidate',
        stage: 'QUEUED',
        status: 'PENDING',
        progress: 0,
        message: 'Queued for reprocessing…',
        warnings: []
      };
    });

    setBatchReprocessState({
      show: true,
      status: 'IN_PROGRESS',
      queue: initialQueue,
      currentIndex: 0,
      total: selectedIds.length
    });

    try {
      const response = await fetch('/api/candidates/batch-reprocess-stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ candidate_ids: selectedIds })
      });

      if (!response.body) throw new Error('ReadableStream not supported.');

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const block of lines) {
          for (const line of block.split('\n')) {
            if (line.startsWith('data: ')) {
              try {
                const event = JSON.parse(line.substring(6));
                setBatchReprocessState(prev => {
                  if (!prev) return null;
                  const newQueue = [...prev.queue];
                  const idx = newQueue.findIndex(item => item.candidate_id === event.candidate_id);
                  if (idx !== -1) {
                    newQueue[idx] = {
                      ...newQueue[idx],
                      candidate_name: event.candidate_name || newQueue[idx].candidate_name,
                      stage: event.stage,
                      status: event.status,
                      progress: event.progress,
                      message: event.message,
                      warnings: event.warnings || newQueue[idx].warnings
                    };
                  }
                  const allDone = newQueue.every(i => i.status === 'SUCCESS' || i.status === 'FAILED' || i.status === 'SKIPPED');
                  return {
                    ...prev,
                    queue: newQueue,
                    currentIndex: event.batch_index || prev.currentIndex,
                    status: allDone ? 'COMPLETED' : 'IN_PROGRESS'
                  };
                });
              } catch (err) {
                console.error('Error parsing SSE batch reprocess event:', err);
              }
            }
          }
        }
      }
    } catch (err) {
      console.error('Batch reprocess stream failed:', err);
      setBatchReprocessState(prev => prev ? { ...prev, status: 'FAILED' } : null);
    }
  };


  const fetchCandidates = () => {
    fetch('/api/candidates')
      .then((res) => res.json())
      .then((data) => {
        if (Array.isArray(data)) {
          setCandidates(data);
        }
      })
      .catch((err) => console.error(err));
  };

  useEffect(() => {
    if (location.pathname === '/') {
      fetchCandidates();
    }
  }, [location.pathname]);

  const handleFileUpload = async (e) => {
    const files = Array.from(e.target.files);
    if (!files.length) return;

    setShowUploadManager(true);
    setUploadQueue(files.map(f => ({
      file_name: f.name,
      stage: 'QUEUED',
      status: 'PENDING',
      progress: 0,
      message: ''
    })));

    const formData = new FormData();
    files.forEach(f => formData.append('files', f));

    try {
      const response = await fetch('/api/candidates/upload-stream', {
        method: 'POST',
        body: formData
      });

      if (!response.body) throw new Error('ReadableStream not supported.');

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      
      let buffer = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        
        // Keep the last incomplete chunk in the buffer
        buffer = lines.pop() || '';
        
        for (const block of lines) {
          const linesInBlock = block.split('\n');
          for (const line of linesInBlock) {
            if (line.startsWith('data: ')) {
              try {
                const event = JSON.parse(line.substring(6));
                setUploadQueue(prev => {
                  const newQ = [...prev];
                  const idx = newQ.findIndex(item => item.file_name === event.file_name);
                  if (idx !== -1) {
                    newQ[idx] = { ...newQ[idx], ...event };
                  }
                  return newQ;
                });
              } catch (err) {
                console.error('Error parsing SSE event:', err);
              }
            }
          }
        }
      }
    } catch (err) {
      console.error('Upload stream failed:', err);
    }
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) {
      setIsSearching(false);
      setSearchProgress(null);
      setSearchWarnings([]);
      lastSearchedQueryRef.current = '';
      insightControllersRef.current.forEach((controller) => controller.abort());
      insightControllersRef.current.clear();
      setInsights({});
      fetchCandidates();
      return;
    }

    setIsSearching(true);
    setSearchProgress({ stage: 'STARTING', progress: 0, message: 'Initializing search…' });
    setCandidates([]);
    lastSearchedQueryRef.current = query;

    const requestBody = { query_text: query, top_k: 10 };
    if (city.trim()) requestBody.city = city.trim();
    if (title.trim()) requestBody.title = title.trim();
    if (minYoe.trim() && !isNaN(parseFloat(minYoe))) requestBody.min_yoe = parseFloat(minYoe);

    try {
      const response = await fetch('/api/search/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody)
      });

      if (!response.body) throw new Error('ReadableStream not supported.');

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      
      let buffer = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';
        
        for (const block of lines) {
          const linesInBlock = block.split('\n');
          for (const line of linesInBlock) {
            if (line.startsWith('data: ')) {
              try {
                const event = JSON.parse(line.substring(6));
                
                if (event.stage === 'COMPLETE') {
                  if (event.data) {
                    setSearchWarnings(event.data.warnings || []);
                    if (event.data.results) {
                      const mapped = event.data.results.map((resItem) => {
                        const info = resItem.candidate_info || {};
                        return {
                          id: resItem.candidate_id,
                          first_name: info.first_name || 'Candidate',
                          last_name: info.last_name || `#${resItem.candidate_id.substring(0, 6)}`,
                          current_title: info.current_title || '',
                          current_company: info.current_company || '',
                          current_city: info.current_city || '',
                          availability_status: info.availability_status || 'ACTIVE',
                          rrf_score: resItem.rrf_score,
                          match_percentage: resItem.match_percentage,
                          rank: resItem.rank,
                          match_scorecard: resItem.match_scorecard
                        };
                      });
                      setCandidates(mapped);
                      
                      // Trigger AI insights for top 3 candidates
                      if (aiNotesEnabledRef.current) {
                        fireTopInsights(mapped, query);
                      }
                    }
                  }
                  
                  // Clear progress after short delay
                  setTimeout(() => {
                    setSearchProgress(null);
                    setIsSearching(false);
                  }, 800);
                } else if (event.stage === 'ERROR') {
                  console.error('Search error:', event.message);
                  setSearchWarnings([`Search failed: ${event.message}`]);
                  setIsSearching(false);
                  setSearchProgress(null);
                } else {
                  setSearchProgress({
                    stage: event.stage,
                    progress: event.progress,
                    message: event.message
                  });
                }
              } catch (err) {
                console.error('Error parsing search event:', err);
              }
            }
          }
        }
      }
    } catch (err) {
      console.error('Search stream failed:', err);
      setIsSearching(false);
      setSearchProgress(null);
    }
  };


  const toggleMenu = (e, id) => {
    e.stopPropagation();
    setOpenMenuId(openMenuId === id ? null : id);
  };

  const confirmDeleteCandidate = async () => {
    if (!deleteCandidate) return;
    setIsDeleting(true);
    setListDeleteError(null);
    try {
      const res = await fetch(`/api/candidates/${deleteCandidate.id}`, { method: 'DELETE' });
      if (res.ok || res.status === 204) {
        setCandidates(prev => prev.filter(c => c.id !== deleteCandidate.id));
        setDeleteCandidate(null);
      } else {
        setListDeleteError('Failed to delete candidate.');
      }
    } catch (err) {
      console.error('Error deleting candidate:', err);
      setListDeleteError('An error occurred while deleting candidate.');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleReprocess = async (e, id) => {
    if (e) e.stopPropagation();
    setOpenMenuId(null);
    const cand = candidates.find(c => c.id === id);
    const candidateName = cand ? `${cand.first_name} ${cand.last_name}` : 'Candidate';

    setReprocessState({
      show: true,
      candidateId: id,
      candidateName: candidateName,
      stage: 'STARTING',
      status: 'IN_PROGRESS',
      progress: 5,
      message: 'Initiating re-processing…'
    });

    try {
      const response = await fetch(`/api/candidates/${id}/reprocess-stream`, { method: 'POST' });
      if (!response.body) throw new Error('ReadableStream not supported.');

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const block of lines) {
          for (const line of block.split('\n')) {
            if (line.startsWith('data: ')) {
              try {
                const event = JSON.parse(line.substring(6));
                setReprocessState(prev => prev ? {
                  ...prev,
                  stage: event.stage,
                  status: event.status,
                  progress: event.progress,
                  message: event.message,
                  candidateName: event.candidate_name || prev.candidateName,
                  warnings: event.warnings || prev.warnings || []
                } : null);
              } catch (err) {
                console.error('Error parsing SSE event:', err);
              }
            }
          }
        }
      }
    } catch (err) {
      console.error('Reprocess stream failed:', err);
      setReprocessState(prev => prev ? {
        ...prev,
        stage: 'ERROR',
        status: 'FAILED',
        progress: 100,
        message: 'Failed to re-process candidate data.'
      } : null);
    }
  };

  return (
    <div className="min-h-screen p-8 max-w-7xl mx-auto flex flex-col gap-8" onClick={() => setOpenMenuId(null)}>
      {/* Header */}
      <header className="flex justify-between items-center mb-2">
        <div>
          <h1 className="text-3xl font-bold font-display tracking-tight text-neutral-100">Candidate Intelligence Platform</h1>
          <p className="text-neutral-400 mt-1">Local-first, zero-cloud candidate retrieval & CRM platform.</p>
        </div>
        <div className="flex items-center gap-3">
          <label className="bg-emerald-600 hover:bg-emerald-700 text-white px-5 py-2.5 rounded-xl font-medium cursor-pointer transition-colors shadow-lg shadow-emerald-900/20 flex items-center gap-2 text-sm">
            <Upload size={18} />
            <span>Upload Resume(s)</span>
            <input type="file" accept=".pdf,.docx,.doc,.txt" multiple className="hidden" onChange={handleFileUpload} />
          </label>
        </div>
      </header>

      {/* Search Bar */}
      <section className="surface-panel p-6 rounded-2xl">
        <form onSubmit={handleSearch} className="flex flex-wrap gap-4">
          <div className="relative flex-1 min-w-[240px]">
            <Search className="absolute left-4 top-3.5 h-5 w-5 text-neutral-500" />
            <input 
              type="text" 
              placeholder="Search candidates by skills, location, or experience..." 
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full bg-neutral-900/50 border border-neutral-700 rounded-xl pl-12 pr-4 py-3 text-neutral-200 placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-[border-color,box-shadow]"
            />
            {query.length > 0 && (
              <button 
                type="button"
                onClick={() => {
                  setQuery('');
                  setIsSearching(false);
                  setSearchProgress(null);
                  setSearchWarnings([]);
                  lastSearchedQueryRef.current = '';
                  insightControllersRef.current.forEach((controller) => controller.abort());
                  insightControllersRef.current.clear();
                  setInsights({});
                  fetch('/api/candidates')
                    .then((res) => res.json())
                    .then((data) => {
                      if (Array.isArray(data)) setCandidates(data);
                    })
                    .catch((err) => console.error(err));
                }}
                className="absolute right-4 top-3.5 text-neutral-400 hover:text-neutral-200"
              >
                <X size={20} />
              </button>
            )}
          </div>
          
          <div className="relative flex-1 min-w-[160px]">
            <MapPin className="absolute left-4 top-3.5 h-5 w-5 text-neutral-500" />
            <input
              type="text"
              placeholder="City"
              value={city}
              onChange={(e) => setCity(e.target.value)}
              className="w-full bg-neutral-900/50 border border-neutral-700 rounded-xl pl-10 pr-4 py-3 text-neutral-200 placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-[border-color,box-shadow]"
              title="Filter by city (exact match)"
            />
          </div>
          
          <div className="relative flex-1 min-w-[160px]">
            <Briefcase className="absolute left-4 top-3.5 h-5 w-5 text-neutral-500" />
            <input
              type="text"
              placeholder="Job Title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full bg-neutral-900/50 border border-neutral-700 rounded-xl pl-10 pr-4 py-3 text-neutral-200 placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-[border-color,box-shadow]"
              title="Filter by job title (exact match)"
            />
          </div>
          
          <div className="relative flex-1 min-w-[140px]">
            <input
              type="number"
              step="0.5"
              min="0"
              placeholder="Min Years"
              value={minYoe}
              onChange={(e) => setMinYoe(e.target.value)}
              className="w-full bg-neutral-900/50 border border-neutral-700 rounded-xl pl-4 pr-4 py-3 text-neutral-200 placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-[border-color,box-shadow]"
              title="Filter by minimum years of experience (decimals allowed, e.g. 2.5)"
            />
          </div>
          
          {(city || title || minYoe) && (
            <button
              type="button"
              onClick={() => {
                setCity('');
                setTitle('');
                setMinYoe('');
              }}
              className="flex items-center gap-1.5 text-neutral-400 hover:text-red-400 px-3 py-3 shrink-0 transition-colors"
              title="Clear filters"
              aria-label="Clear filters"
            >
              <XCircle size={18} />
              <span className="text-sm font-medium">Clear</span>
            </button>
          )}
          
          <button
            type="button"
            onClick={toggleAiNotes}
            title={aiNotesEnabled ? 'AI notes on - click to disable' : 'AI notes off - click to enable'}
            role="checkbox"
            aria-checked={aiNotesEnabled}
            aria-label="Toggle AI Notes"
            className="text-neutral-400 hover:text-emerald-400 flex items-center gap-2 font-medium shrink-0 transition-colors"
          >
            {aiNotesEnabled ? (
              <CheckSquare size={20} className="text-emerald-400" />
            ) : (
              <Square size={20} />
            )}
            <span className="text-sm whitespace-nowrap">AI Notes</span>
          </button>
          <button type="submit" disabled={isSearching} className="bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white px-8 py-3 rounded-xl font-medium transition-colors shadow-lg shadow-emerald-900/20 shrink-0">
            {isSearching ? 'Searching…' : 'Search'}
          </button>
        </form>
      </section>

      {/* Search Progress */}
      {searchProgress && (
        <section className="surface-panel p-5 rounded-2xl border border-emerald-500/30 bg-emerald-950/20 transition-colors animate-in fade-in slide-in-from-top-4 duration-300">
          <div className="flex justify-between items-center mb-3">
            <span className="text-sm font-medium text-emerald-300 flex items-center gap-2">
              <RefreshCw size={16} className="animate-spin text-emerald-400" />
              {searchProgress.message}
            </span>
            <span className="text-sm font-bold text-emerald-400 font-mono bg-emerald-500/10 px-2 py-1 rounded-md">{searchProgress.progress}%</span>
          </div>
          <div className="w-full bg-neutral-900/80 rounded-full h-2.5 overflow-hidden shadow-inner">
            <div 
              className="bg-emerald-500 h-full rounded-full transition-[width] duration-300 ease-out"
              style={{ width: `${searchProgress.progress}%` }}
            />
          </div>
        </section>
      )}

      {/* Search Warning Banner */}
      {searchWarnings && searchWarnings.length > 0 && (
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-2xl p-4 flex items-start gap-3 text-amber-300 text-sm font-medium shadow-lg shadow-amber-950/20">
          <AlertCircle size={20} className="text-amber-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <span className="font-bold text-amber-200">Search Notice (Skipped components / fallbacks):</span>
            <ul className="list-disc list-inside space-y-1 text-amber-300/90 text-xs">
              {searchWarnings.map((w, idx) => (
                <li key={idx}>{w}</li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Master Select */}
      <div className="flex justify-between items-center bg-neutral-900/50 p-4 rounded-xl border border-neutral-800">
        <div className="flex items-center gap-3">
          <button
            onClick={toggleSelectAll}
            role="checkbox"
            aria-checked={candidates.length > 0 && selectedIds.length === candidates.length}
            aria-label="Select all candidates"
            className="text-neutral-400 hover:text-emerald-400 flex items-center gap-2 font-medium"
          >
            {candidates.length > 0 && selectedIds.length === candidates.length ? (
              <CheckSquare size={20} className="text-emerald-400" />
            ) : selectedIds.length > 0 ? (
              <div className="w-5 h-5 bg-emerald-500/20 border-2 border-emerald-400 rounded-sm flex items-center justify-center">
                <div className="w-2.5 h-0.5 bg-emerald-400 rounded-full" />
              </div>
            ) : (
              <Square size={20} />
            )}
            <span className="text-sm">Select All</span>
          </button>
          
          {selectedIds.length > 0 && (
            <span className="text-sm text-emerald-300 bg-emerald-500/10 px-2.5 py-0.5 rounded-full border border-emerald-500/20">
              {selectedIds.length} selected
            </span>
          )}
        </div>
      </div>

      {/* Candidate List Grid */}
      <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">

        {candidates.map((candidate) => {
          const isSelected = selectedIds.includes(candidate.id);
          return (
            <div 
              key={candidate.id} 
              onClick={() => navigate(`/candidate/${candidate.id}`)}
              className={`surface-panel p-6 rounded-2xl transition-colors cursor-pointer group flex flex-col justify-between relative border ${
                isSelected
                  ? 'border-emerald-500 bg-emerald-950/20 ring-2 ring-emerald-500/40'
                  : 'hover:border-emerald-500/50 border-neutral-800/80'
              }`}
            >
              <div>
                <div className="flex justify-between items-start mb-4">
                  <div className="flex items-center gap-3">
                    <button
                      onClick={(e) => toggleSelectCandidate(e, candidate.id)}
                      role="checkbox"
                      aria-checked={isSelected}
                      aria-label={isSelected ? "Deselect candidate" : "Select candidate"}
                      className="text-neutral-400 hover:text-emerald-400 p-1 rounded-md transition-colors shrink-0"
                      title={isSelected ? "Deselect candidate" : "Select candidate"}
                    >
                      {isSelected ? (
                        <CheckSquare size={20} className="text-emerald-400 fill-emerald-500/20" />
                      ) : (
                        <Square size={20} className="text-neutral-500 hover:text-neutral-300" />
                      )}
                    </button>
                    <div className="bg-emerald-950/60 border border-emerald-500/30 p-2.5 rounded-full text-emerald-400 shrink-0">
                      <User size={18} />
                    </div>
                    <div>
                    <h3 className="font-semibold text-lg text-neutral-100 group-hover:text-emerald-300 transition-colors">
                      {candidate.first_name} {candidate.last_name}
                    </h3>
                    <div className="flex items-center gap-2 mt-1">
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                        candidate.availability_status === 'ACTIVE' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 
                        'bg-neutral-700 text-neutral-300 border border-neutral-600'
                      }`}>
                        {candidate.availability_status}
                      </span>
                      {candidate.match_percentage != null && candidate.match_percentage > 0 && (
                        <span className={`text-xs px-2 py-0.5 rounded-full font-bold flex items-center gap-1 border ${
                          candidate.match_percentage >= 80 ? 'bg-emerald-500 text-black border-emerald-400' :
                          candidate.match_percentage >= 50 ? 'bg-transparent text-emerald-300 border-emerald-400/60' :
                          'bg-amber-500/15 text-amber-300 border-amber-500/30'
                        }`}>
                          <span className="font-extrabold text-[9px] uppercase tracking-wider bg-neutral-800/80 px-1 rounded-sm border border-neutral-700/80 text-neutral-300">Match</span>
                          {candidate.match_percentage}%
                        </span>
                      )}
                      {candidate.rank != null && (
                        <span className="text-[10px] font-mono font-bold text-neutral-400 bg-neutral-800/80 border border-neutral-700 px-1.5 py-0.5 rounded">#{candidate.rank}</span>
                      )}
                    </div>
                  </div>
                </div>
                
                {/* Action Menu */}
                <div className="relative">
                  <button 
                    onClick={(e) => toggleMenu(e, candidate.id)}
                    className="text-neutral-400 hover:text-neutral-200 p-1 rounded hover:bg-neutral-800 transition-colors"
                  >
                    <MoreVertical size={18} />
                  </button>
                  
                  {openMenuId === candidate.id && (
                    <div className="absolute right-0 top-8 w-44 bg-neutral-900 border border-neutral-700 rounded-xl shadow-xl overflow-hidden z-10" onClick={(e) => e.stopPropagation()}>
                      <button 
                        onClick={(e) => { e.stopPropagation(); navigate(`/candidate/${candidate.id}`); }}
                        className="w-full text-left px-4 py-2 text-sm text-neutral-300 hover:bg-neutral-800 hover:text-neutral-100 transition-colors flex items-center gap-2"
                      >
                        <User size={14} /> View Details
                      </button>
                      <a
                        href={`/api/candidates/${candidate.id}/file`}
                        download
                        onClick={(e) => e.stopPropagation()}
                        className="w-full text-left px-4 py-2 text-sm text-neutral-300 hover:bg-neutral-800 hover:text-neutral-100 transition-colors flex items-center gap-2"
                      >
                        <Download size={14} /> Download Resume
                      </a>
                      <button 
                        onClick={(e) => handleReprocess(e, candidate.id)}
                        className="w-full text-left px-4 py-2 text-sm text-neutral-300 hover:bg-neutral-800 hover:text-neutral-100 transition-colors flex items-center gap-2"
                      >
                        <RefreshCw size={14} /> Re-process Data
                      </button>
                      <button 
                        onClick={(e) => {
                          e.stopPropagation();
                          setOpenMenuId(null);
                          setDeleteCandidate(candidate);
                        }}
                        className="w-full text-left px-4 py-2 text-sm text-red-400 hover:bg-red-950/40 hover:text-red-300 transition-colors flex items-center gap-2 border-t border-neutral-800"
                      >
                        <Trash2 size={14} /> Delete Candidate
                      </button>
                    </div>
                  )}
                </div>

              </div>
              
              <div className="space-y-3 mt-4 text-sm text-neutral-400">
                {candidate.current_title && (
                  <div className="flex items-center gap-2">
                    <Briefcase size={16} className="text-neutral-500" />
                    <span>{candidate.current_title} {candidate.current_company ? `at ${candidate.current_company}` : ''}</span>
                  </div>
                )}
                {candidate.current_city && (
                  <div className="flex items-center gap-2">
                    <MapPin size={16} className="text-neutral-500" />
                    <span>{candidate.current_city}</span>
                  </div>
                )}
              </div>
              
              {/* AI Insight Box */}
              {query.trim().length > 0 && aiNotesEnabled && (
                <div className="mt-4 border-t border-neutral-800 pt-4" onClick={e => e.stopPropagation()}>
                  {insights[candidate.id] ? (
                    <div className="bg-emerald-950/20 border border-emerald-500/20 rounded-lg p-3 text-sm">
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-emerald-300 font-semibold flex items-center gap-1.5 text-xs uppercase tracking-wider">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                          AI Rationale
                        </span>
                        {insights[candidate.id].status === 'loading' ? (
                          <button 
                            onClick={(e) => { e.stopPropagation(); insights[candidate.id].controller?.abort(); }}
                            className="text-neutral-400 hover:text-red-400 text-xs px-2 py-1 rounded transition-colors"
                          >
                            Cancel AI Note
                          </button>
                        ) : (
                          <button 
                            onClick={(e) => { e.stopPropagation(); generateInsight(candidate.id, query); }}
                            className="text-emerald-400 hover:text-emerald-300 text-xs px-2 py-1 rounded transition-colors"
                          >
                            Regenerate
                          </button>
                        )}
                      </div>
                      <div className="text-neutral-300 leading-relaxed text-sm max-h-32 overflow-y-auto">
                        {insights[candidate.id].text}
                        {insights[candidate.id].status === 'loading' && <span className="inline-block w-1.5 h-3 ml-1 bg-emerald-400 animate-pulse"></span>}
                        {insights[candidate.id].status === 'cancelled' && <span className="text-neutral-500 italic block mt-1 text-xs">Generation cancelled.</span>}
                        {insights[candidate.id].status === 'error' && <span className="text-red-400 italic block mt-1 text-xs">{insights[candidate.id].errorMessage || 'Generation failed.'}</span>}
                      </div>
                    </div>
                  ) : (
                    <button 
                      onClick={(e) => { e.stopPropagation(); generateInsight(candidate.id, query); }}
                      className="w-full py-2 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 rounded-lg text-sm transition-colors flex items-center justify-center gap-2"
                    >
                      Generate AI Note
                    </button>
                  )}
                </div>
              )}
            </div>
            
            <div className="mt-6 pt-4 border-t border-neutral-700/50 flex justify-end">
              <button onClick={() => navigate(`/candidate/${candidate.id}`)} className="flex items-center gap-1 text-sm text-emerald-400 hover:text-emerald-300 font-medium">
                View Profile <ChevronRight size={16} />
              </button>
            </div>
          </div>
        );
      })}
        
        {candidates.length === 0 && (
          <div className="col-span-full py-16 text-center text-neutral-500 border-2 border-dashed border-neutral-700/60 rounded-2xl bg-neutral-900/30">
            <User className="mx-auto h-10 w-10 text-neutral-600 mb-3" />
            <p className="text-neutral-300 font-medium">No candidates found</p>
            <p className="text-sm text-neutral-500 mt-1">Ingest resumes or adjust your search filter.</p>
          </div>
        )}
      </section>

      {/* Upload Manager Modal */}
      {showUploadManager && (
        <div className="fixed inset-0 bg-neutral-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-modal">
          <div className="surface-panel border-neutral-700 max-w-3xl w-full rounded-2xl p-6 relative max-h-[80vh] flex flex-col">
            <div className="flex justify-between items-center mb-6">
              <div>
                <h2 className="text-xl font-bold text-neutral-100 flex items-center gap-2">
                  <Upload size={22} className="text-emerald-400" /> Upload Manager
                </h2>
                <p className="text-sm text-neutral-400 mt-1">Processing and ingesting candidates…</p>
              </div>
              <button 
                onClick={() => {
                  setShowUploadManager(false);
                  fetchCandidates();
                }}
                className="bg-neutral-800 hover:bg-neutral-700 text-neutral-200 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
              >
                Done
              </button>
            </div>
            
            <div className="flex-1 overflow-y-auto space-y-4 pr-2">
              {uploadQueue.map((item, idx) => (
                <div key={idx} className="bg-neutral-900/50 border border-neutral-800 rounded-xl p-4 flex flex-col gap-3">
                  <div className="flex justify-between items-start">
                    <div className="font-medium text-neutral-200 text-sm truncate max-w-[240px]" title={item.file_name}>
                      {item.file_name}
                    </div>
                    <div className="flex items-center gap-2 text-xs font-medium">
                      {item.status === 'SUCCESS' && (
                        item.used_ai_fallback ? (
                          <span className="flex items-center gap-1 text-emerald-300 bg-emerald-500/15 px-2.5 py-1 rounded border border-emerald-500/30">
                            <span className="font-bold text-[9px] uppercase bg-emerald-500/30 px-1 rounded-sm text-emerald-200">AI</span> Ingested (Model: {item.model_name || 'llama3.2'})
                          </span>
                        ) : (
                          <span className="flex items-center gap-1 text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded border border-emerald-500/20">
                            <CheckCircle2 size={13}/> Completed (Rule-based)
                          </span>
                        )
                      )}
                      {item.status === 'SUCCESS' && item.resolution_action === 'REVIEW' && item.matched_candidate_id && (
                        <button
                          onClick={(e) => { e.stopPropagation(); navigate(`/candidate/${item.matched_candidate_id}`); }}
                          className="flex items-center gap-1 text-amber-400 bg-amber-500/10 px-2 py-1 rounded border border-amber-500/20 hover:bg-amber-500/20 transition-colors"
                          title={`Possible duplicate of candidate ${item.matched_candidate_id}`}
                        >
                          Possible duplicate?
                        </button>
                      )}
                      {item.status === 'FAILED' && <span className="flex items-center gap-1 text-red-400 bg-red-500/10 px-2 py-1 rounded border border-red-500/20"><AlertCircle size={14}/> Failed</span>}
                      {item.status === 'SKIPPED_DUPLICATE' && <span className="flex items-center gap-1 text-amber-400 bg-amber-500/10 px-2 py-1 rounded border border-amber-500/20"><RefreshCw size={14}/> Duplicate</span>}
                      {item.status === 'IN_PROGRESS' && (
                        item.stage === 'AI_EXTRACTION' || item.used_ai ? (
                          <span className="flex items-center gap-1 text-emerald-300 bg-emerald-500/20 px-2.5 py-1 rounded border border-emerald-500/40 animate-pulse font-medium">
                            <span className="font-bold text-[9px] uppercase bg-emerald-500/30 px-1 rounded-sm text-emerald-200">AI</span> Extraction ({item.model_name || 'llama3.2'})
                          </span>
                        ) : (
                          <span className="text-emerald-400 animate-pulse font-medium">{item.stage_detail || item.stage}…</span>
                        )
                      )}
                      {item.status === 'PENDING' && <span className="text-neutral-500">Queued</span>}
                    </div>
                  </div>
                  
                  <div className="w-full bg-neutral-800 rounded-full h-2 overflow-hidden">
                    <div 
                      className={`h-2 rounded-full transition-[width] duration-300 ${
                        item.status === 'FAILED' ? 'bg-red-500' : 
                        item.status === 'SKIPPED_DUPLICATE' ? 'bg-amber-500' : 
                        item.status === 'SUCCESS' && item.used_ai_fallback ? 'bg-emerald-500' :
                        item.status === 'SUCCESS' ? 'bg-emerald-500' :
                        item.stage === 'AI_EXTRACTION' || item.used_ai ? 'bg-emerald-500 animate-pulse' :
                        'bg-emerald-500'
                      }`} 
                      style={{ width: `${item.progress}%` }}
                    ></div>
                  </div>
                  
                  {item.stage === 'AI_EXTRACTION' && (
                    <div className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-emerald-950/80 border border-emerald-500/30 text-emerald-200 text-xs shadow-inner">
                      <span className="font-bold text-[10px] uppercase bg-emerald-500/30 px-1.5 py-0.5 rounded-sm text-emerald-200">AI Process</span>
                      <span>{item.message || `Extracting candidate facts using local AI model (${item.model_name || 'llama3.2'})…`}</span>
                    </div>
                  )}

                  {item.stage !== 'AI_EXTRACTION' && item.message && (
                    <div className="text-xs text-neutral-400 flex items-center justify-between">
                      <span>{item.message}</span>
                      <span className="font-mono text-neutral-500">{item.progress}%</span>
                    </div>
                  )}

                  {item.candidate_name && item.status === 'SUCCESS' && (
                    <div className="text-xs text-emerald-400/90 font-medium">
                      Candidate created: {item.candidate_name}
                    </div>
                  )}

                  {item.warnings && item.warnings.length > 0 && (
                    <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-2.5 mt-1 text-xs text-amber-300">
                      <div className="font-semibold text-amber-400 flex items-center gap-1.5 mb-1">
                        <AlertCircle size={14} className="shrink-0 text-amber-400" />
                        <span>Skipped steps / notices:</span>
                      </div>
                      <ul className="list-disc list-inside space-y-0.5 text-amber-300/90 text-[11px]">
                        {item.warnings.map((w, wIdx) => (
                          <li key={wIdx}>{w}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ))}

            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteCandidate && (
        <div className="fixed inset-0 bg-neutral-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-confirm">
          <div className="bg-neutral-900 border border-neutral-700 max-w-md w-full rounded-2xl p-6 relative shadow-2xl">
            <div className="flex items-center gap-3 text-red-400 mb-4">
              <div className="p-2 bg-red-500/10 rounded-xl border border-red-500/20">
                <Trash2 size={24} />
              </div>
              <h3 className="text-lg font-bold text-neutral-100">Delete Candidate</h3>
            </div>
            
            <p className="text-neutral-300 text-sm mb-2">
              Are you sure you want to delete <span className="font-semibold text-neutral-100">{deleteCandidate.first_name} {deleteCandidate.last_name}</span>?
            </p>
            <p className="text-neutral-400 text-xs mb-6">
              This action will permanently remove candidate details, timeline events, and search index vectors.
            </p>

            {listDeleteError && (
              <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-3 mb-4 text-xs text-red-300" role="alert">
                {listDeleteError}
              </div>
            )}

            <div className="flex justify-end gap-3">
              <button
                onClick={() => { setDeleteCandidate(null); setListDeleteError(null); }}
                disabled={isDeleting}
                className="px-4 py-2 bg-neutral-800 hover:bg-neutral-700 text-neutral-300 text-sm font-medium rounded-xl transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={confirmDeleteCandidate}
                disabled={isDeleting}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-xl transition-colors shadow-lg shadow-red-900/20 disabled:opacity-50 flex items-center gap-2"
              >
                {isDeleting ? 'Deleting...' : 'Delete Permanently'}
              </button>
            </div>
          </div>
        </div>
      )}
      {/* Reprocess Manager Modal */}
      {reprocessState?.show && (
        <div className="fixed inset-0 bg-neutral-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-modal">
          <div className="surface-panel border-neutral-700 max-w-lg w-full rounded-2xl p-6 relative flex flex-col gap-4 shadow-2xl">
            <div className="flex justify-between items-center border-b border-neutral-800 pb-4">
              <div>
                <h2 className="text-xl font-bold text-neutral-100 flex items-center gap-2">
                  <RefreshCw size={22} className={`text-emerald-400 ${reprocessState.status === 'IN_PROGRESS' ? 'animate-spin' : ''}`} />
                  Reprocessing Candidate
                </h2>
                <p className="text-sm text-neutral-400 mt-0.5">Re-indexing resume and vector embeddings</p>
              </div>
              <button 
                onClick={() => {
                  setReprocessState(null);
                  fetchCandidates();
                }}
                disabled={reprocessState.status === 'IN_PROGRESS'}
                className="bg-neutral-800 hover:bg-neutral-700 disabled:opacity-50 text-neutral-200 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
              >
                {reprocessState.status === 'SUCCESS' ? 'Done' : 'Close'}
              </button>
            </div>
            
            <div className="bg-neutral-900/60 border border-neutral-800 rounded-xl p-5 flex flex-col gap-4">
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="font-semibold text-neutral-200 text-base">{reprocessState.candidateName}</h3>
                  <p className="text-xs text-neutral-400 mt-0.5">ID: {reprocessState.candidateId}</p>
                </div>
                <div className="flex items-center gap-2 text-xs font-medium">
                  {reprocessState.status === 'SUCCESS' && (
                    reprocessState.used_ai_fallback ? (
                      <span className="flex items-center gap-1 text-emerald-300 bg-emerald-500/15 px-2.5 py-1 rounded-full border border-emerald-500/30">
                        AI Re-indexed ({reprocessState.model_name || 'llama3.2'})
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20">
                        <CheckCircle2 size={14}/> Completed
                      </span>
                    )
                  )}
                  {reprocessState.status === 'FAILED' && (
                    <span className="flex items-center gap-1 text-red-400 bg-red-500/10 px-2.5 py-1 rounded-full border border-red-500/20">
                      <AlertCircle size={14}/> Failed
                    </span>
                  )}
                  {reprocessState.status === 'IN_PROGRESS' && (
                    reprocessState.stage === 'AI_EXTRACTION' || reprocessState.used_ai ? (
                      <span className="text-emerald-300 bg-emerald-500/20 px-2.5 py-1 rounded-full border border-emerald-500/40 animate-pulse flex items-center gap-1">
                        AI Model Active ({reprocessState.model_name || 'llama3.2'})
                      </span>
                    ) : (
                      <span className="text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20 animate-pulse">
                        {reprocessState.stage_detail || reprocessState.stage}…
                      </span>
                    )
                  )}
                </div>
              </div>
              
              <div className="space-y-1.5">
                <div className="flex justify-between text-xs text-neutral-400 font-medium">
                  <span>{reprocessState.message || 'Processing…'}</span>
                  <span>{reprocessState.progress}%</span>
                </div>
                <div className="w-full bg-neutral-800 rounded-full h-2 overflow-hidden">
                  <div 
                    className={`h-2 rounded-full transition-[width] duration-300 ${
                      reprocessState.status === 'FAILED' ? 'bg-red-500' : 
                      reprocessState.status === 'SUCCESS' && reprocessState.used_ai_fallback ? 'bg-emerald-500' :
                      reprocessState.status === 'SUCCESS' ? 'bg-emerald-500' : 
                      reprocessState.stage === 'AI_EXTRACTION' || reprocessState.used_ai ? 'bg-emerald-500 animate-pulse shadow-md shadow-emerald-500/30' :
                      'bg-emerald-500'
                    }`} 
                    style={{ width: `${reprocessState.progress}%` }}
                  ></div>
                </div>
              </div>

              {reprocessState.stage === 'AI_EXTRACTION' && (
                <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-emerald-950/50 border border-emerald-500/40 text-emerald-200 text-xs shadow-inner animate-pulse">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse shrink-0"></span>
                  <span><strong>AI Model Active:</strong> Extracting missing profile fields using local LLM ({reprocessState.model_name || 'llama3.2'})...</span>
                </div>
              )}

              {/* Stage Stepper Badges */}
              <div className="grid grid-cols-5 gap-2 pt-2 border-t border-neutral-800/80 text-[11px] text-neutral-400 text-center font-medium">
                <div className={`p-1.5 rounded-lg border ${['FETCHING_RESUME', 'ENTITY_RESOLUTION', 'AI_EXTRACTION', 'UPDATING_FTS', 'GENERATING_VECTORS', 'LOGGING_TIMELINE', 'COMPLETED'].indexOf(reprocessState.stage) >= 0 ? 'bg-emerald-950/50 border-emerald-500/40 text-emerald-300' : 'bg-neutral-900 border-neutral-800'}`}>
                  1. Profile
                </div>
                <div className={`p-1.5 rounded-lg border ${reprocessState.stage === 'AI_EXTRACTION' ? 'bg-emerald-950/80 border-emerald-500/60 text-emerald-200 font-bold animate-pulse flex items-center justify-center gap-1' : ['ENTITY_RESOLUTION', 'UPDATING_FTS', 'GENERATING_VECTORS', 'LOGGING_TIMELINE', 'COMPLETED'].indexOf(reprocessState.stage) >= 0 ? 'bg-emerald-950/50 border-emerald-500/40 text-emerald-300' : 'bg-neutral-900 border-neutral-800'}`}>
                  {reprocessState.stage === 'AI_EXTRACTION' ? '2. AI Model' : '2. Entities'}
                </div>
                <div className={`p-1.5 rounded-lg border ${['UPDATING_FTS', 'GENERATING_VECTORS', 'LOGGING_TIMELINE', 'COMPLETED'].indexOf(reprocessState.stage) >= 0 ? 'bg-emerald-950/50 border-emerald-500/40 text-emerald-300' : 'bg-neutral-900 border-neutral-800'}`}>
                  3. FTS Search
                </div>
                <div className={`p-1.5 rounded-lg border ${['GENERATING_VECTORS', 'LOGGING_TIMELINE', 'COMPLETED'].indexOf(reprocessState.stage) >= 0 ? 'bg-emerald-950/50 border-emerald-500/40 text-emerald-300' : 'bg-neutral-900 border-neutral-800'}`}>
                  4. Vectors
                </div>
                <div className={`p-1.5 rounded-lg border ${['LOGGING_TIMELINE', 'COMPLETED'].indexOf(reprocessState.stage) >= 0 ? 'bg-emerald-950/50 border-emerald-500/40 text-emerald-300' : 'bg-neutral-900 border-neutral-800'}`}>
                  5. Timeline
                </div>
              </div>

              {reprocessState.warnings && reprocessState.warnings.length > 0 && (
                <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-3 text-xs text-amber-300">
                  <div className="font-semibold text-amber-400 flex items-center gap-1.5 mb-1">
                    <AlertCircle size={14} className="shrink-0 text-amber-400" />
                    <span>Reprocessing warnings / skipped steps:</span>
                  </div>
                  <ul className="list-disc list-inside space-y-0.5 text-amber-300/90 text-[11px]">
                    {reprocessState.warnings.map((w, wIdx) => (
                      <li key={wIdx}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Floating Action Bar for Multi-Selection */}
      {selectedIds.length > 0 && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-bar bg-neutral-900/90 border border-emerald-500/40 backdrop-blur-xl px-6 py-3.5 rounded-2xl shadow-[0_10px_40px_rgba(0,0,0,0.5)] flex items-center gap-6 animate-in slide-in-from-bottom-6 duration-300 whitespace-nowrap max-w-fit">
          <div className="flex items-center gap-3 border-r border-neutral-700/80 pr-5 shrink-0">
            <button 
              onClick={toggleSelectAll}
              className="text-neutral-300 hover:text-white text-xs font-semibold flex items-center gap-1.5 bg-neutral-800/80 hover:bg-neutral-800 px-3 py-1.5 rounded-lg border border-neutral-700 transition-colors whitespace-nowrap shrink-0"
            >
              {selectedIds.length === candidates.length && candidates.length > 0 ? (
                <> <CheckSquare size={15} className="text-emerald-400 shrink-0" /> Deselect All </>
              ) : (
                <> <Square size={15} className="text-neutral-400 shrink-0" /> Select All </>
              )}
            </button>
            <span className="text-sm font-semibold text-emerald-300 whitespace-nowrap shrink-0">
              {selectedIds.length} candidate{selectedIds.length > 1 ? 's' : ''} selected
            </span>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <button
              onClick={handleBatchReprocess}
              className="bg-emerald-600 hover:bg-emerald-500 text-white px-4 py-2 rounded-xl text-sm font-medium flex items-center gap-2 transition-colors shadow-lg shadow-emerald-900/30 border border-emerald-400/30 whitespace-nowrap shrink-0"
            >
              <RefreshCw size={16} className="shrink-0" /> Re-process ({selectedIds.length})
            </button>
            <button
              onClick={handleBatchDownloadResumes}
              className="bg-neutral-800 hover:bg-neutral-700 text-neutral-200 px-4 py-2 rounded-xl text-sm font-medium flex items-center gap-2 transition-colors border border-neutral-700 whitespace-nowrap shrink-0"
            >
              <Download size={16} className="shrink-0" /> Download Resumes
            </button>
            <button
              onClick={() => setShowBatchDeleteModal(true)}
              className="bg-red-600/90 hover:bg-red-600 text-white px-4 py-2 rounded-xl text-sm font-medium flex items-center gap-2 transition-colors shadow-lg shadow-red-950/30 border border-red-500/30 whitespace-nowrap shrink-0"
            >
              <Trash2 size={16} className="shrink-0" /> Delete ({selectedIds.length})
            </button>
            <button
              onClick={clearSelection}
              className="text-neutral-400 hover:text-neutral-200 p-1.5 rounded-lg hover:bg-neutral-800 transition-colors ml-1 shrink-0"
              title="Clear selection"
            >
              <X size={18} />
            </button>
          </div>
        </div>
      )}

      {/* Batch Delete Confirmation Modal */}
      {showBatchDeleteModal && (
        <div className="fixed inset-0 bg-neutral-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-confirm">
          <div className="bg-neutral-900 border border-neutral-700 max-w-md w-full rounded-2xl p-6 relative shadow-2xl">
            <div className="flex items-center gap-3 text-red-400 mb-4">
              <div className="p-2 bg-red-500/10 rounded-xl border border-red-500/20">
                <Trash2 size={24} />
              </div>
              <h3 className="text-lg font-bold text-neutral-100">Delete {selectedIds.length} Candidates</h3>
            </div>
            
            <p className="text-neutral-300 text-sm mb-2">
              Are you sure you want to permanently delete <span className="font-semibold text-neutral-100">{selectedIds.length} selected candidate(s)</span>?
            </p>
            <div className="bg-neutral-950/60 border border-neutral-800 rounded-xl p-3 max-h-32 overflow-y-auto my-3 text-xs text-neutral-400 space-y-1">
              {candidates
                .filter(c => selectedIds.includes(c.id))
                .map(c => (
                  <div key={c.id} className="truncate">• {c.first_name} {c.last_name}</div>
                ))
              }
            </div>
            <p className="text-neutral-400 text-xs mb-6">
              This action will permanently purge their profile records, uploaded resumes, timeline logs, and vector search embeddings.
            </p>

            {batchDeleteError && (
              <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-3 mb-4 text-xs text-red-300" role="alert">
                {batchDeleteError}
              </div>
            )}

            <div className="flex justify-end gap-3">
              <button
                onClick={() => { setShowBatchDeleteModal(false); setBatchDeleteError(null); }}
                disabled={isBatchDeleting}
                className="px-4 py-2 bg-neutral-800 hover:bg-neutral-700 text-neutral-300 text-sm font-medium rounded-xl transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={confirmBatchDelete}
                disabled={isBatchDeleting}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-xl transition-colors shadow-lg shadow-red-900/20 disabled:opacity-50 flex items-center gap-2"
              >
                {isBatchDeleting ? 'Deleting...' : `Delete ${selectedIds.length} Candidates`}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Batch Reprocess Manager Modal */}
      {batchReprocessState?.show && (
        <div className="fixed inset-0 bg-neutral-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-modal">
          <div className="surface-panel border-neutral-700 max-w-2xl w-full rounded-2xl p-6 relative flex flex-col max-h-[80vh] shadow-2xl">
            <div className="flex justify-between items-center border-b border-neutral-800 pb-4 mb-4">
              <div>
                <h2 className="text-xl font-bold text-neutral-100 flex items-center gap-2">
                  <RefreshCw size={22} className={`text-emerald-400 ${batchReprocessState.status === 'IN_PROGRESS' ? 'animate-spin' : ''}`} />
                  Batch Reprocessing ({batchReprocessState.queue.filter(i => i.status === 'SUCCESS' || i.status === 'SKIPPED').length} / {batchReprocessState.total})
                </h2>
                <p className="text-sm text-neutral-400 mt-0.5">Re-indexing profile entities, FTS, and vector embeddings in real time</p>
              </div>
              <button 
                onClick={() => {
                  setBatchReprocessState(null);
                  fetchCandidates();
                  setSelectedIds([]);
                }}
                disabled={batchReprocessState.status === 'IN_PROGRESS'}
                className="bg-neutral-800 hover:bg-neutral-700 disabled:opacity-50 text-neutral-200 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
              >
                {batchReprocessState.status === 'COMPLETED' ? 'Done' : 'Close'}
              </button>
            </div>
            
            <div className="flex-1 overflow-y-auto space-y-3 pr-2">
              {batchReprocessState.queue.map((item, idx) => (
                <div key={item.candidate_id || idx} className="bg-neutral-900/60 border border-neutral-800 rounded-xl p-4 flex flex-col gap-2">
                  <div className="flex justify-between items-center">
                    <div>
                      <h4 className="font-semibold text-neutral-200 text-sm">{item.candidate_name}</h4>
                      <p className="text-[11px] text-neutral-500">{item.message}</p>
                    </div>
                    <div className="flex items-center gap-2 text-xs font-medium">
                      {item.status === 'SUCCESS' && (
                        item.used_ai_fallback ? (
                          <span className="flex items-center gap-1 text-emerald-300 bg-emerald-500/15 px-2 py-0.5 rounded border border-emerald-500/30 text-[11px]">
                            AI Re-indexed ({item.model_name || 'llama3.2'})
                          </span>
                        ) : (
                          <span className="flex items-center gap-1 text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                            <CheckCircle2 size={13}/> Completed
                          </span>
                        )
                      )}
                      {item.status === 'FAILED' && (
                        <span className="flex items-center gap-1 text-red-400 bg-red-500/10 px-2 py-0.5 rounded border border-red-500/20">
                          <AlertCircle size={13}/> Failed
                        </span>
                      )}
                      {item.status === 'SKIPPED' && (
                        <span className="flex items-center gap-1 text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                          <RefreshCw size={13}/> Skipped
                        </span>
                      )}
                      {item.status === 'IN_PROGRESS' && (
                        item.stage === 'AI_EXTRACTION' || item.used_ai ? (
                          <span className="flex items-center gap-1 text-emerald-300 bg-emerald-500/20 px-2 py-0.5 rounded border border-emerald-500/40 animate-pulse text-[11px]">
                            AI Model Active ({item.model_name || 'llama3.2'})
                          </span>
                        ) : (
                          <span className="text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20 animate-pulse">
                            {item.stage_detail || item.stage}…
                          </span>
                        )
                      )}
                      {item.status === 'PENDING' && (
                        <span className="text-neutral-500">Queued</span>
                      )}
                    </div>
                  </div>

                  <div className="w-full bg-neutral-800 rounded-full h-1.5 overflow-hidden">
                    <div 
                      className={`h-1.5 rounded-full transition-[width] duration-300 ${
                        item.status === 'FAILED' ? 'bg-red-500' : 
                        item.status === 'SUCCESS' && item.used_ai_fallback ? 'bg-emerald-500' :
                        item.status === 'SUCCESS' ? 'bg-emerald-500' : 
                        item.status === 'SKIPPED' ? 'bg-amber-500' : 
                        item.stage === 'AI_EXTRACTION' || item.used_ai ? 'bg-emerald-500 animate-pulse shadow-sm shadow-emerald-500/30' :
                        'bg-emerald-500'
                      }`}
                      style={{ width: `${item.progress}%` }}
                    ></div>
                  </div>

                  {item.stage === 'AI_EXTRACTION' && (
                    <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-emerald-950/40 border border-emerald-500/30 text-emerald-300 text-[11px]">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse shrink-0"></span>
                      <span>{item.message || `Running local AI Model (${item.model_name || 'llama3.2'})…`}</span>
                    </div>
                  )}

                  {item.warnings && item.warnings.length > 0 && (
                    <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-2 text-xs text-amber-300 mt-1">
                      <div className="font-semibold text-amber-400 flex items-center gap-1 text-[11px]">
                        <AlertCircle size={12} className="shrink-0 text-amber-400" />
                        <span>Warnings / Skipped steps:</span>
                      </div>
                      <ul className="list-disc list-inside space-y-0.5 text-amber-300/90 text-[10px] mt-0.5">
                        {item.warnings.map((w, wIdx) => (
                          <li key={wIdx}>{w}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

export default CandidateList;
