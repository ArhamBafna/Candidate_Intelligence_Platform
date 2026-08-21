import { useState, useEffect } from 'react';
import { MagnifyingGlass as Search, MapPin, Briefcase, CaretRight as ChevronRight, User, Upload, CheckCircle as CheckCircle2, WarningCircle as AlertCircle, ArrowsClockwise as RefreshCw, DotsThreeVertical as MoreVertical, DownloadSimple as Download, Trash as Trash2, CheckSquare, Square, X } from '@phosphor-icons/react';
import { useNavigate, useLocation } from 'react-router-dom';

function CandidateList() {
  const navigate = useNavigate();
  const location = useLocation();
  const [candidates, setCandidates] = useState([]);
  const [query, setQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [openMenuId, setOpenMenuId] = useState(null);
  const [deleteCandidate, setDeleteCandidate] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);
  
  // Search & Warnings State
  const [searchWarnings, setSearchWarnings] = useState([]);
  const [searchProgress, setSearchProgress] = useState(null);
  const [insights, setInsights] = useState({});
  
  // Upload Manager State
  const [showUploadManager, setShowUploadManager] = useState(false);
  const [uploadQueue, setUploadQueue] = useState([]);

  // Reprocess Manager State
  const [reprocessState, setReprocessState] = useState(null);

  // Multi-Selection State
  const [selectedIds, setSelectedIds] = useState([]);
  const [showBatchDeleteModal, setShowBatchDeleteModal] = useState(false);
  const [isBatchDeleting, setIsBatchDeleting] = useState(false);
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

  const generateInsight = async (candidateId, searchQuery) => {
    const controller = new AbortController();
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
                if (event.token) {
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
      setInsights(prev => ({
        ...prev,
        [candidateId]: { ...prev[candidateId], status: 'done' }
      }));
    } catch (err) {
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
        alert('Failed to delete selected candidates.');
      }
    } catch (err) {
      console.error('Batch delete failed:', err);
      alert('An error occurred during batch delete.');
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
        message: 'Queued for reprocessing...',
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
      fetchCandidates();
      return;
    }

    setIsSearching(true);
    setSearchProgress({ stage: 'STARTING', progress: 0, message: 'Initializing search...' });
    setCandidates([]);

    try {
      const response = await fetch('/api/search/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query_text: query, top_k: 10 })
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
                          current_title: info.current_title || 'Software Engineer',
                          current_company: info.current_company || 'Tech Corp',
                          current_city: info.current_city || 'Remote',
                          availability_status: info.availability_status || 'ACTIVE',
                          rrf_score: resItem.rrf_score,
                          match_percentage: resItem.match_percentage,
                          rank: resItem.rank,
                          match_scorecard: resItem.match_scorecard
                        };
                      });
                      setCandidates(mapped);
                      
                      // Trigger AI insights for top 3 candidates
                      mapped.slice(0, 3).forEach(c => {
                        generateInsight(c.id, query);
                      });
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
    try {
      const res = await fetch(`/api/candidates/${deleteCandidate.id}`, { method: 'DELETE' });
      if (res.ok || res.status === 204) {
        setCandidates(prev => prev.filter(c => c.id !== deleteCandidate.id));
        setDeleteCandidate(null);
      } else {
        alert('Failed to delete candidate.');
      }
    } catch (err) {
      console.error('Error deleting candidate:', err);
      alert('An error occurred while deleting candidate.');
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
      message: 'Initiating re-processing...'
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
          <h1 className="text-3xl font-bold font-display tracking-tight text-slate-100">Candidate Intelligence Platform</h1>
          <p className="text-slate-400 mt-1">Local-first, zero-cloud candidate retrieval & CRM platform.</p>
        </div>
        <div className="flex items-center gap-3">
          <label className="bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-2.5 rounded-xl font-medium cursor-pointer transition-colors shadow-lg shadow-indigo-900/20 flex items-center gap-2 text-sm">
            <Upload size={18} />
            <span>Upload Resume(s)</span>
            <input type="file" accept=".pdf,.docx,.doc,.txt" multiple className="hidden" onChange={handleFileUpload} />
          </label>
        </div>
      </header>

      {/* Search Bar */}
      <section className="glass-panel p-6 rounded-2xl">
        <form onSubmit={handleSearch} className="flex gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-4 top-3.5 h-5 w-5 text-slate-500" />
            <input 
              type="text" 
              placeholder="Search candidates by skills, location, or experience..." 
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full bg-slate-900/50 border border-slate-700 rounded-xl pl-12 pr-4 py-3 text-slate-200 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
            />
            {query.length > 0 && (
              <button 
                type="button"
                onClick={() => {
                  setQuery('');
                  setIsSearching(false);
                  setSearchProgress(null);
                  setSearchWarnings([]);
                  fetch('/api/candidates')
                    .then((res) => res.json())
                    .then((data) => {
                      if (Array.isArray(data)) setCandidates(data);
                    })
                    .catch((err) => console.error(err));
                }}
                className="absolute right-4 top-3.5 text-slate-400 hover:text-slate-200"
              >
                <X size={20} />
              </button>
            )}
          </div>
          <button type="submit" className="bg-indigo-600 hover:bg-indigo-700 text-white px-8 py-3 rounded-xl font-medium transition-colors shadow-lg shadow-indigo-900/20">
            {isSearching ? 'Search' : 'Search'}
          </button>
        </form>
      </section>

      {/* Search Progress */}
      {searchProgress && (
        <section className="glass-panel p-5 rounded-2xl border border-indigo-500/30 bg-indigo-950/20 shadow-[0_0_20px_rgba(99,102,241,0.1)] transition-all animate-in fade-in slide-in-from-top-4 duration-300">
          <div className="flex justify-between items-center mb-3">
            <span className="text-sm font-medium text-indigo-300 flex items-center gap-2">
              <RefreshCw size={16} className="animate-spin text-indigo-400" />
              {searchProgress.message}
            </span>
            <span className="text-sm font-bold text-indigo-400 font-mono bg-indigo-500/10 px-2 py-1 rounded-md">{searchProgress.progress}%</span>
          </div>
          <div className="w-full bg-slate-900/80 rounded-full h-2.5 overflow-hidden shadow-inner">
            <div 
              className="bg-indigo-500 h-full rounded-full transition-all duration-300 ease-out"
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
      <div className="flex justify-between items-center bg-slate-900/50 p-4 rounded-xl border border-slate-800">
        <div className="flex items-center gap-3">
          <button
            onClick={toggleSelectAll}
            className="text-slate-400 hover:text-indigo-400 flex items-center gap-2 font-medium"
          >
            {candidates.length > 0 && selectedIds.length === candidates.length ? (
              <CheckSquare size={20} className="text-indigo-400" />
            ) : selectedIds.length > 0 ? (
              <div className="w-5 h-5 bg-indigo-500/20 border-2 border-indigo-400 rounded-sm flex items-center justify-center">
                <div className="w-2.5 h-0.5 bg-indigo-400 rounded-full" />
              </div>
            ) : (
              <Square size={20} />
            )}
            <span className="text-sm">Select All</span>
          </button>
          
          {selectedIds.length > 0 && (
            <span className="text-sm text-indigo-300 bg-indigo-500/10 px-2.5 py-0.5 rounded-full border border-indigo-500/20">
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
              className={`glass-panel p-6 rounded-2xl transition-all cursor-pointer group flex flex-col justify-between relative border ${
                isSelected 
                  ? 'border-indigo-500 bg-indigo-950/20 ring-2 ring-indigo-500/40 shadow-[0_0_20px_rgba(99,102,241,0.15)]' 
                  : 'hover:border-indigo-500/50 border-slate-800/80'
              }`}
            >
              <div>
                <div className="flex justify-between items-start mb-4">
                  <div className="flex items-center gap-3">
                    <button
                      onClick={(e) => toggleSelectCandidate(e, candidate.id)}
                      className="text-slate-400 hover:text-indigo-400 p-1 rounded-md transition-colors shrink-0"
                      title={isSelected ? "Deselect candidate" : "Select candidate"}
                    >
                      {isSelected ? (
                        <CheckSquare size={20} className="text-indigo-400 fill-indigo-500/20" />
                      ) : (
                        <Square size={20} className="text-slate-500 hover:text-slate-300" />
                      )}
                    </button>
                    <div className="bg-indigo-950/60 border border-indigo-500/30 p-2.5 rounded-full text-indigo-400 shrink-0">
                      <User size={18} />
                    </div>
                    <div>
                    <h3 className="font-semibold text-lg text-slate-100 group-hover:text-indigo-300 transition-colors">
                      {candidate.first_name} {candidate.last_name}
                    </h3>
                    <div className="flex items-center gap-2 mt-1">
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                        candidate.availability_status === 'ACTIVE' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 
                        'bg-slate-700 text-slate-300 border border-slate-600'
                      }`}>
                        {candidate.availability_status}
                      </span>
                      {candidate.match_percentage != null && candidate.match_percentage > 0 && (
                        <span className={`text-xs px-2 py-0.5 rounded-full font-bold flex items-center gap-1 border ${
                          candidate.match_percentage >= 80 ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30' :
                          candidate.match_percentage >= 50 ? 'bg-indigo-500/15 text-indigo-300 border-indigo-500/30' :
                          'bg-amber-500/15 text-amber-300 border-amber-500/30'
                        }`}>
                          <span className="font-extrabold text-[9px] uppercase tracking-wider bg-slate-800/80 px-1 rounded-sm border border-slate-700/80 text-slate-300">Match</span>
                          {candidate.match_percentage}%
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                
                {/* Action Menu */}
                <div className="relative">
                  <button 
                    onClick={(e) => toggleMenu(e, candidate.id)}
                    className="text-slate-400 hover:text-slate-200 p-1 rounded hover:bg-slate-800 transition-colors"
                  >
                    <MoreVertical size={18} />
                  </button>
                  
                  {openMenuId === candidate.id && (
                    <div className="absolute right-0 top-8 w-44 bg-slate-900 border border-slate-700 rounded-xl shadow-xl overflow-hidden z-10" onClick={(e) => e.stopPropagation()}>
                      <button 
                        onClick={(e) => { e.stopPropagation(); navigate(`/candidate/${candidate.id}`); }}
                        className="w-full text-left px-4 py-2 text-sm text-slate-300 hover:bg-slate-800 hover:text-slate-100 transition-colors flex items-center gap-2"
                      >
                        <User size={14} /> View Details
                      </button>
                      <a
                        href={`/api/candidates/${candidate.id}/file`}
                        download
                        onClick={(e) => e.stopPropagation()}
                        className="w-full text-left px-4 py-2 text-sm text-slate-300 hover:bg-slate-800 hover:text-slate-100 transition-colors flex items-center gap-2"
                      >
                        <Download size={14} /> Download Resume
                      </a>
                      <button 
                        onClick={(e) => handleReprocess(e, candidate.id)}
                        className="w-full text-left px-4 py-2 text-sm text-slate-300 hover:bg-slate-800 hover:text-slate-100 transition-colors flex items-center gap-2"
                      >
                        <RefreshCw size={14} /> Re-process Data
                      </button>
                      <button 
                        onClick={(e) => {
                          e.stopPropagation();
                          setOpenMenuId(null);
                          setDeleteCandidate(candidate);
                        }}
                        className="w-full text-left px-4 py-2 text-sm text-red-400 hover:bg-red-950/40 hover:text-red-300 transition-colors flex items-center gap-2 border-t border-slate-800"
                      >
                        <Trash2 size={14} /> Delete Candidate
                      </button>
                    </div>
                  )}
                </div>

              </div>
              
              <div className="space-y-3 mt-4 text-sm text-slate-400">
                {candidate.current_title && (
                  <div className="flex items-center gap-2">
                    <Briefcase size={16} className="text-slate-500" />
                    <span>{candidate.current_title} {candidate.current_company ? `at ${candidate.current_company}` : ''}</span>
                  </div>
                )}
                {candidate.current_city && (
                  <div className="flex items-center gap-2">
                    <MapPin size={16} className="text-slate-500" />
                    <span>{candidate.current_city}</span>
                  </div>
                )}
              </div>
              
              {/* AI Insight Box */}
              {query.trim().length > 0 && (
                <div className="mt-4 border-t border-slate-800 pt-4" onClick={e => e.stopPropagation()}>
                  {insights[candidate.id] ? (
                    <div className="bg-indigo-950/20 border border-indigo-500/20 rounded-lg p-3 text-sm">
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-indigo-300 font-semibold flex items-center gap-1.5 text-xs uppercase tracking-wider">
                          <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse"></span>
                          AI Rationale
                        </span>
                        {insights[candidate.id].status === 'loading' ? (
                          <button 
                            onClick={(e) => { e.stopPropagation(); insights[candidate.id].controller?.abort(); }}
                            className="text-slate-400 hover:text-red-400 text-xs px-2 py-1 rounded transition-colors"
                          >
                            Cancel AI Note
                          </button>
                        ) : (
                          <button 
                            onClick={(e) => { e.stopPropagation(); generateInsight(candidate.id, query); }}
                            className="text-indigo-400 hover:text-indigo-300 text-xs px-2 py-1 rounded transition-colors"
                          >
                            Regenerate
                          </button>
                        )}
                      </div>
                      <div className="text-slate-300 leading-relaxed text-sm max-h-32 overflow-y-auto">
                        {insights[candidate.id].text}
                        {insights[candidate.id].status === 'loading' && <span className="inline-block w-1.5 h-3 ml-1 bg-indigo-400 animate-pulse"></span>}
                        {insights[candidate.id].status === 'cancelled' && <span className="text-slate-500 italic block mt-1 text-xs">Generation cancelled.</span>}
                        {insights[candidate.id].status === 'error' && <span className="text-red-400 italic block mt-1 text-xs">Generation failed.</span>}
                      </div>
                    </div>
                  ) : (
                    <button 
                      onClick={(e) => { e.stopPropagation(); generateInsight(candidate.id, query); }}
                      className="w-full py-2 bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/30 text-indigo-300 rounded-lg text-sm transition-colors flex items-center justify-center gap-2"
                    >
                      Generate AI Note
                    </button>
                  )}
                </div>
              )}
            </div>
            
            <div className="mt-6 pt-4 border-t border-slate-700/50 flex justify-end">
              <button className="flex items-center gap-1 text-sm text-indigo-400 hover:text-indigo-300 font-medium">
                View Profile <ChevronRight size={16} />
              </button>
            </div>
          </div>
        );
      })}
        
        {candidates.length === 0 && (
          <div className="col-span-full py-16 text-center text-slate-500 border-2 border-dashed border-slate-700/60 rounded-2xl bg-slate-900/30">
            <User className="mx-auto h-10 w-10 text-slate-600 mb-3" />
            <p className="text-slate-300 font-medium">No candidates found</p>
            <p className="text-sm text-slate-500 mt-1">Ingest resumes or adjust your search filter.</p>
          </div>
        )}
      </section>

      {/* Upload Manager Modal */}
      {showUploadManager && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-[60]">
          <div className="glass-panel border-slate-700 max-w-3xl w-full rounded-2xl p-6 relative max-h-[80vh] flex flex-col">
            <div className="flex justify-between items-center mb-6">
              <div>
                <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
                  <Upload size={22} className="text-indigo-400" /> Upload Manager
                </h2>
                <p className="text-sm text-slate-400 mt-1">Processing and ingesting candidates...</p>
              </div>
              <button 
                onClick={() => {
                  setShowUploadManager(false);
                  fetchCandidates();
                }}
                className="bg-slate-800 hover:bg-slate-700 text-slate-200 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
              >
                Done
              </button>
            </div>
            
            <div className="flex-1 overflow-y-auto space-y-4 pr-2">
              {uploadQueue.map((item, idx) => (
                <div key={idx} className="bg-slate-900/50 border border-slate-800 rounded-xl p-4 flex flex-col gap-3">
                  <div className="flex justify-between items-start">
                    <div className="font-medium text-slate-200 text-sm truncate max-w-[240px]" title={item.file_name}>
                      {item.file_name}
                    </div>
                    <div className="flex items-center gap-2 text-xs font-medium">
                      {item.status === 'SUCCESS' && (
                        item.used_ai_fallback ? (
                          <span className="flex items-center gap-1 text-indigo-300 bg-indigo-500/15 px-2.5 py-1 rounded border border-indigo-500/30">
                            <span className="font-bold text-[9px] uppercase bg-indigo-500/30 px-1 rounded-sm text-indigo-200">AI</span> Ingested (Model: {item.model_name || 'llama3.2'})
                          </span>
                        ) : (
                          <span className="flex items-center gap-1 text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded border border-emerald-500/20">
                            <CheckCircle2 size={13}/> Completed (Rule-based)
                          </span>
                        )
                      )}
                      {item.status === 'FAILED' && <span className="flex items-center gap-1 text-red-400 bg-red-500/10 px-2 py-1 rounded border border-red-500/20"><AlertCircle size={14}/> Failed</span>}
                      {item.status === 'SKIPPED_DUPLICATE' && <span className="flex items-center gap-1 text-amber-400 bg-amber-500/10 px-2 py-1 rounded border border-amber-500/20"><RefreshCw size={14}/> Duplicate</span>}
                      {item.status === 'IN_PROGRESS' && (
                        item.stage === 'AI_EXTRACTION' || item.used_ai ? (
                          <span className="flex items-center gap-1 text-indigo-300 bg-indigo-500/20 px-2.5 py-1 rounded border border-indigo-500/40 animate-pulse font-medium">
                            <span className="font-bold text-[9px] uppercase bg-indigo-500/30 px-1 rounded-sm text-indigo-200">AI</span> Extraction ({item.model_name || 'llama3.2'})
                          </span>
                        ) : (
                          <span className="text-indigo-400 animate-pulse font-medium">{item.stage_detail || item.stage}...</span>
                        )
                      )}
                      {item.status === 'PENDING' && <span className="text-slate-500">Queued</span>}
                    </div>
                  </div>
                  
                  <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                    <div 
                      className={`h-2 rounded-full transition-all duration-300 ${
                        item.status === 'FAILED' ? 'bg-red-500' : 
                        item.status === 'SKIPPED_DUPLICATE' ? 'bg-amber-500' : 
                        item.status === 'SUCCESS' && item.used_ai_fallback ? 'bg-indigo-500' :
                        item.status === 'SUCCESS' ? 'bg-emerald-500' :
                        item.stage === 'AI_EXTRACTION' || item.used_ai ? 'bg-indigo-500 animate-pulse' :
                        'bg-indigo-500'
                      }`} 
                      style={{ width: `${item.progress}%` }}
                    ></div>
                  </div>
                  
                  {item.stage === 'AI_EXTRACTION' && (
                    <div className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-indigo-950/80 border border-indigo-500/30 text-indigo-200 text-xs shadow-inner">
                      <span className="font-bold text-[10px] uppercase bg-indigo-500/30 px-1.5 py-0.5 rounded-sm text-indigo-200">AI Process</span>
                      <span>{item.message || `Extracting candidate facts using local AI model (${item.model_name || 'llama3.2'})...`}</span>
                    </div>
                  )}

                  {item.stage !== 'AI_EXTRACTION' && item.message && (
                    <div className="text-xs text-slate-400 flex items-center justify-between">
                      <span>{item.message}</span>
                      <span className="font-mono text-slate-500">{item.progress}%</span>
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
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-[70]">
          <div className="bg-slate-900 border border-slate-700 max-w-md w-full rounded-2xl p-6 relative shadow-2xl">
            <div className="flex items-center gap-3 text-red-400 mb-4">
              <div className="p-2 bg-red-500/10 rounded-xl border border-red-500/20">
                <Trash2 size={24} />
              </div>
              <h3 className="text-lg font-bold text-slate-100">Delete Candidate</h3>
            </div>
            
            <p className="text-slate-300 text-sm mb-2">
              Are you sure you want to delete <span className="font-semibold text-slate-100">{deleteCandidate.first_name} {deleteCandidate.last_name}</span>?
            </p>
            <p className="text-slate-400 text-xs mb-6">
              This action will permanently remove candidate details, timeline events, and search index vectors.
            </p>
            
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setDeleteCandidate(null)}
                disabled={isDeleting}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium rounded-xl transition-colors"
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
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-[60]">
          <div className="glass-panel border-slate-700 max-w-lg w-full rounded-2xl p-6 relative flex flex-col gap-4 shadow-2xl">
            <div className="flex justify-between items-center border-b border-slate-800 pb-4">
              <div>
                <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
                  <RefreshCw size={22} className={`text-indigo-400 ${reprocessState.status === 'IN_PROGRESS' ? 'animate-spin' : ''}`} />
                  Reprocessing Candidate
                </h2>
                <p className="text-sm text-slate-400 mt-0.5">Re-indexing resume and vector embeddings</p>
              </div>
              <button 
                onClick={() => {
                  setReprocessState(null);
                  fetchCandidates();
                }}
                disabled={reprocessState.status === 'IN_PROGRESS'}
                className="bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
              >
                {reprocessState.status === 'SUCCESS' ? 'Done' : 'Close'}
              </button>
            </div>
            
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 flex flex-col gap-4">
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="font-semibold text-slate-200 text-base">{reprocessState.candidateName}</h3>
                  <p className="text-xs text-slate-400 mt-0.5">ID: {reprocessState.candidateId}</p>
                </div>
                <div className="flex items-center gap-2 text-xs font-medium">
                  {reprocessState.status === 'SUCCESS' && (
                    reprocessState.used_ai_fallback ? (
                      <span className="flex items-center gap-1 text-purple-300 bg-purple-500/15 px-2.5 py-1 rounded-full border border-purple-500/30">
                        <Sparkles size={14} className="text-purple-400"/> AI Re-indexed ({reprocessState.model_name || 'llama3.2'})
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
                      <span className="text-purple-300 bg-purple-500/20 px-2.5 py-1 rounded-full border border-purple-500/40 animate-pulse flex items-center gap-1">
                        <Sparkles size={13} className="text-purple-400 animate-spin"/> AI Model Active ({reprocessState.model_name || 'llama3.2'})
                      </span>
                    ) : (
                      <span className="text-indigo-400 bg-indigo-500/10 px-2.5 py-1 rounded-full border border-indigo-500/20 animate-pulse">
                        {reprocessState.stage_detail || reprocessState.stage}...
                      </span>
                    )
                  )}
                </div>
              </div>
              
              <div className="space-y-1.5">
                <div className="flex justify-between text-xs text-slate-400 font-medium">
                  <span>{reprocessState.message || 'Processing...'}</span>
                  <span>{reprocessState.progress}%</span>
                </div>
                <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                  <div 
                    className={`h-2 rounded-full transition-all duration-300 ${
                      reprocessState.status === 'FAILED' ? 'bg-red-500' : 
                      reprocessState.status === 'SUCCESS' && reprocessState.used_ai_fallback ? 'bg-gradient-to-r from-purple-500 to-indigo-500' :
                      reprocessState.status === 'SUCCESS' ? 'bg-emerald-500' : 
                      reprocessState.stage === 'AI_EXTRACTION' || reprocessState.used_ai ? 'bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 animate-pulse shadow-md shadow-purple-500/30' :
                      'bg-indigo-500'
                    }`} 
                    style={{ width: `${reprocessState.progress}%` }}
                  ></div>
                </div>
              </div>

              {reprocessState.stage === 'AI_EXTRACTION' && (
                <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-purple-950/50 border border-purple-500/40 text-purple-200 text-xs shadow-inner animate-pulse">
                  <Sparkles size={16} className="text-purple-400 shrink-0 animate-bounce" />
                  <span><strong>AI Model Active:</strong> Extracting missing profile fields using local LLM ({reprocessState.model_name || 'llama3.2'})...</span>
                </div>
              )}

              {/* Stage Stepper Badges */}
              <div className="grid grid-cols-5 gap-2 pt-2 border-t border-slate-800/80 text-[11px] text-slate-400 text-center font-medium">
                <div className={`p-1.5 rounded-lg border ${['FETCHING_RESUME', 'ENTITY_RESOLUTION', 'AI_EXTRACTION', 'UPDATING_FTS', 'GENERATING_VECTORS', 'LOGGING_TIMELINE', 'COMPLETED'].indexOf(reprocessState.stage) >= 0 ? 'bg-indigo-950/50 border-indigo-500/40 text-indigo-300' : 'bg-slate-900 border-slate-800'}`}>
                  1. Profile
                </div>
                <div className={`p-1.5 rounded-lg border ${reprocessState.stage === 'AI_EXTRACTION' ? 'bg-purple-950/80 border-purple-500/60 text-purple-200 font-bold animate-pulse flex items-center justify-center gap-1' : ['ENTITY_RESOLUTION', 'UPDATING_FTS', 'GENERATING_VECTORS', 'LOGGING_TIMELINE', 'COMPLETED'].indexOf(reprocessState.stage) >= 0 ? 'bg-indigo-950/50 border-indigo-500/40 text-indigo-300' : 'bg-slate-900 border-slate-800'}`}>
                  {reprocessState.stage === 'AI_EXTRACTION' ? '2. AI Model' : '2. Entities'}
                </div>
                <div className={`p-1.5 rounded-lg border ${['UPDATING_FTS', 'GENERATING_VECTORS', 'LOGGING_TIMELINE', 'COMPLETED'].indexOf(reprocessState.stage) >= 0 ? 'bg-indigo-950/50 border-indigo-500/40 text-indigo-300' : 'bg-slate-900 border-slate-800'}`}>
                  3. FTS Search
                </div>
                <div className={`p-1.5 rounded-lg border ${['GENERATING_VECTORS', 'LOGGING_TIMELINE', 'COMPLETED'].indexOf(reprocessState.stage) >= 0 ? 'bg-indigo-950/50 border-indigo-500/40 text-indigo-300' : 'bg-slate-900 border-slate-800'}`}>
                  4. Vectors
                </div>
                <div className={`p-1.5 rounded-lg border ${['LOGGING_TIMELINE', 'COMPLETED'].indexOf(reprocessState.stage) >= 0 ? 'bg-indigo-950/50 border-indigo-500/40 text-indigo-300' : 'bg-slate-900 border-slate-800'}`}>
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
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-[50] bg-slate-900/90 border border-indigo-500/40 backdrop-blur-xl px-6 py-3.5 rounded-2xl shadow-[0_10px_40px_rgba(0,0,0,0.5)] flex items-center gap-6 animate-in slide-in-from-bottom-6 duration-300 whitespace-nowrap max-w-fit">
          <div className="flex items-center gap-3 border-r border-slate-700/80 pr-5 shrink-0">
            <button 
              onClick={toggleSelectAll}
              className="text-slate-300 hover:text-white text-xs font-semibold flex items-center gap-1.5 bg-slate-800/80 hover:bg-slate-800 px-3 py-1.5 rounded-lg border border-slate-700 transition-colors whitespace-nowrap shrink-0"
            >
              {selectedIds.length === candidates.length && candidates.length > 0 ? (
                <> <CheckSquare size={15} className="text-indigo-400 shrink-0" /> Deselect All </>
              ) : (
                <> <Square size={15} className="text-slate-400 shrink-0" /> Select All </>
              )}
            </button>
            <span className="text-sm font-semibold text-indigo-300 whitespace-nowrap shrink-0">
              {selectedIds.length} candidate{selectedIds.length > 1 ? 's' : ''} selected
            </span>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <button
              onClick={handleBatchReprocess}
              className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-xl text-sm font-medium flex items-center gap-2 transition-colors shadow-lg shadow-indigo-900/30 border border-indigo-400/30 whitespace-nowrap shrink-0"
            >
              <RefreshCw size={16} className="shrink-0" /> Re-process ({selectedIds.length})
            </button>
            <button
              onClick={handleBatchDownloadResumes}
              className="bg-slate-800 hover:bg-slate-700 text-slate-200 px-4 py-2 rounded-xl text-sm font-medium flex items-center gap-2 transition-colors border border-slate-700 whitespace-nowrap shrink-0"
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
              className="text-slate-400 hover:text-slate-200 p-1.5 rounded-lg hover:bg-slate-800 transition-colors ml-1 shrink-0"
              title="Clear selection"
            >
              <X size={18} />
            </button>
          </div>
        </div>
      )}

      {/* Batch Delete Confirmation Modal */}
      {showBatchDeleteModal && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-[70]">
          <div className="bg-slate-900 border border-slate-700 max-w-md w-full rounded-2xl p-6 relative shadow-2xl">
            <div className="flex items-center gap-3 text-red-400 mb-4">
              <div className="p-2 bg-red-500/10 rounded-xl border border-red-500/20">
                <Trash2 size={24} />
              </div>
              <h3 className="text-lg font-bold text-slate-100">Delete {selectedIds.length} Candidates</h3>
            </div>
            
            <p className="text-slate-300 text-sm mb-2">
              Are you sure you want to permanently delete <span className="font-semibold text-slate-100">{selectedIds.length} selected candidate(s)</span>?
            </p>
            <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-3 max-h-32 overflow-y-auto my-3 text-xs text-slate-400 space-y-1">
              {candidates
                .filter(c => selectedIds.includes(c.id))
                .map(c => (
                  <div key={c.id} className="truncate">• {c.first_name} {c.last_name}</div>
                ))
              }
            </div>
            <p className="text-slate-400 text-xs mb-6">
              This action will permanently purge their profile records, uploaded resumes, timeline logs, and vector search embeddings.
            </p>
            
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowBatchDeleteModal(false)}
                disabled={isBatchDeleting}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium rounded-xl transition-colors"
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
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-[60]">
          <div className="glass-panel border-slate-700 max-w-2xl w-full rounded-2xl p-6 relative flex flex-col max-h-[80vh] shadow-2xl">
            <div className="flex justify-between items-center border-b border-slate-800 pb-4 mb-4">
              <div>
                <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
                  <RefreshCw size={22} className={`text-indigo-400 ${batchReprocessState.status === 'IN_PROGRESS' ? 'animate-spin' : ''}`} />
                  Batch Reprocessing ({batchReprocessState.queue.filter(i => i.status === 'SUCCESS' || i.status === 'SKIPPED').length} / {batchReprocessState.total})
                </h2>
                <p className="text-sm text-slate-400 mt-0.5">Re-indexing profile entities, FTS, and vector embeddings in real time</p>
              </div>
              <button 
                onClick={() => {
                  setBatchReprocessState(null);
                  fetchCandidates();
                  setSelectedIds([]);
                }}
                disabled={batchReprocessState.status === 'IN_PROGRESS'}
                className="bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
              >
                {batchReprocessState.status === 'COMPLETED' ? 'Done' : 'Close'}
              </button>
            </div>
            
            <div className="flex-1 overflow-y-auto space-y-3 pr-2">
              {batchReprocessState.queue.map((item, idx) => (
                <div key={item.candidate_id || idx} className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex flex-col gap-2">
                  <div className="flex justify-between items-center">
                    <div>
                      <h4 className="font-semibold text-slate-200 text-sm">{item.candidate_name}</h4>
                      <p className="text-[11px] text-slate-500">{item.message}</p>
                    </div>
                    <div className="flex items-center gap-2 text-xs font-medium">
                      {item.status === 'SUCCESS' && (
                        item.used_ai_fallback ? (
                          <span className="flex items-center gap-1 text-purple-300 bg-purple-500/15 px-2 py-0.5 rounded border border-purple-500/30 text-[11px]">
                            <Sparkles size={12} className="text-purple-400"/> AI Re-indexed ({item.model_name || 'llama3.2'})
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
                          <span className="flex items-center gap-1 text-purple-300 bg-purple-500/20 px-2 py-0.5 rounded border border-purple-500/40 animate-pulse text-[11px]">
                            <Sparkles size={12} className="text-purple-400 animate-spin"/> AI Model Active ({item.model_name || 'llama3.2'})
                          </span>
                        ) : (
                          <span className="text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20 animate-pulse">
                            {item.stage_detail || item.stage}...
                          </span>
                        )
                      )}
                      {item.status === 'PENDING' && (
                        <span className="text-slate-500">Queued</span>
                      )}
                    </div>
                  </div>

                  <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                    <div 
                      className={`h-1.5 rounded-full transition-all duration-300 ${
                        item.status === 'FAILED' ? 'bg-red-500' : 
                        item.status === 'SUCCESS' && item.used_ai_fallback ? 'bg-gradient-to-r from-purple-500 to-indigo-500' :
                        item.status === 'SUCCESS' ? 'bg-emerald-500' : 
                        item.status === 'SKIPPED' ? 'bg-amber-500' : 
                        item.stage === 'AI_EXTRACTION' || item.used_ai ? 'bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 animate-pulse shadow-sm shadow-purple-500/30' :
                        'bg-indigo-500'
                      }`}
                      style={{ width: `${item.progress}%` }}
                    ></div>
                  </div>

                  {item.stage === 'AI_EXTRACTION' && (
                    <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-purple-950/40 border border-purple-500/30 text-purple-300 text-[11px]">
                      <Sparkles size={12} className="text-purple-400 shrink-0 animate-bounce" />
                      <span>{item.message || `Running local AI Model (${item.model_name || 'llama3.2'})...`}</span>
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
