import { useState, useEffect } from 'react';
import { Search, MapPin, Briefcase, ChevronRight, User, Upload, CheckCircle2, AlertCircle, RefreshCw, MoreVertical, Download, Trash2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

function CandidateList() {
  const navigate = useNavigate();
  const [candidates, setCandidates] = useState([]);
  const [query, setQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [openMenuId, setOpenMenuId] = useState(null);
  const [deleteCandidate, setDeleteCandidate] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);
  
  // Search & Warnings State
  const [searchWarnings, setSearchWarnings] = useState([]);
  
  // Upload Manager State
  const [showUploadManager, setShowUploadManager] = useState(false);
  const [uploadQueue, setUploadQueue] = useState([]);

  // Reprocess Manager State
  const [reprocessState, setReprocessState] = useState(null);


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
    fetchCandidates();
  }, []);

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

  const handleSearch = (e) => {
    e.preventDefault();
    if (!query.trim()) {
      setIsSearching(false);
      setSearchWarnings([]);
      fetchCandidates();
      return;
    }

    setIsSearching(true);
    fetch('/api/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query_text: query, top_k: 10 })
    })
      .then((res) => res.json())
      .then((data) => {
        if (data) {
          setSearchWarnings(data.warnings || []);
          if (data.results) {
            const mapped = data.results.map((resItem) => {
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
                rank: resItem.rank,
                match_scorecard: resItem.match_scorecard
              };
            });
            setCandidates(mapped);
          }
        }
      })
      .catch((err) => console.error(err));
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
          <h1 className="text-3xl font-bold gradient-text tracking-tight">Candidate Intelligence Platform</h1>
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
          </div>
          <button type="submit" className="bg-indigo-600 hover:bg-indigo-700 text-white px-8 py-3 rounded-xl font-medium transition-colors shadow-lg shadow-indigo-900/20">
            {isSearching ? 'Search' : 'Search'}
          </button>
        </form>
      </section>

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

      {/* Candidate List Grid */}
      <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">

        {candidates.map((candidate) => (
          <div 
            key={candidate.id} 
            onClick={() => navigate(`/candidate/${candidate.id}`)}
            className="glass-panel p-6 rounded-2xl hover:border-indigo-500/50 transition-all cursor-pointer group flex flex-col justify-between relative"
          >
            <div>
              <div className="flex justify-between items-start mb-4">
                <div className="flex items-center gap-3">
                  <div className="bg-indigo-950/60 border border-indigo-500/30 p-3 rounded-full text-indigo-400">
                    <User size={20} />
                  </div>
                  <div>
                    <h3 className="font-semibold text-lg text-slate-100 group-hover:text-indigo-300 transition-colors">
                      {candidate.first_name} {candidate.last_name}
                    </h3>
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                      candidate.availability_status === 'ACTIVE' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 
                      'bg-slate-700 text-slate-300 border border-slate-600'
                    }`}>
                      {candidate.availability_status}
                    </span>
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
            </div>
            
            <div className="mt-6 pt-4 border-t border-slate-700/50 flex justify-end">
              <button className="flex items-center gap-1 text-sm text-indigo-400 hover:text-indigo-300 font-medium">
                View Profile <ChevronRight size={16} />
              </button>
            </div>
          </div>
        ))}
        
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
                    <div className="font-medium text-slate-200 text-sm truncate max-w-[200px]" title={item.file_name}>
                      {item.file_name}
                    </div>
                    <div className="flex items-center gap-2 text-xs font-medium">
                      {item.status === 'SUCCESS' && <span className="flex items-center gap-1 text-emerald-400 bg-emerald-500/10 px-2 py-1 rounded border border-emerald-500/20"><CheckCircle2 size={14}/> Completed</span>}
                      {item.status === 'FAILED' && <span className="flex items-center gap-1 text-red-400 bg-red-500/10 px-2 py-1 rounded border border-red-500/20"><AlertCircle size={14}/> Failed</span>}
                      {item.status === 'SKIPPED_DUPLICATE' && <span className="flex items-center gap-1 text-amber-400 bg-amber-500/10 px-2 py-1 rounded border border-amber-500/20"><RefreshCw size={14}/> Duplicate</span>}
                      {item.status === 'IN_PROGRESS' && <span className="text-indigo-400 animate-pulse">{item.stage}...</span>}
                      {item.status === 'PENDING' && <span className="text-slate-500">Queued</span>}
                    </div>
                  </div>
                  
                  <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                    <div 
                      className={`h-1.5 rounded-full transition-all duration-300 ${
                        item.status === 'FAILED' ? 'bg-red-500' : 
                        item.status === 'SKIPPED_DUPLICATE' ? 'bg-amber-500' : 
                        'bg-indigo-500'
                      }`} 
                      style={{ width: `${item.progress}%` }}
                    ></div>
                  </div>
                  
                  {item.message && (
                    <div className="text-xs text-slate-500 mt-1">
                      {item.message}
                    </div>
                  )}
                  {item.candidate_name && item.status === 'SUCCESS' && (
                    <div className="text-xs text-emerald-500/70 mt-1">
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
                    <span className="flex items-center gap-1 text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20">
                      <CheckCircle2 size={14}/> Completed
                    </span>
                  )}
                  {reprocessState.status === 'FAILED' && (
                    <span className="flex items-center gap-1 text-red-400 bg-red-500/10 px-2.5 py-1 rounded-full border border-red-500/20">
                      <AlertCircle size={14}/> Failed
                    </span>
                  )}
                  {reprocessState.status === 'IN_PROGRESS' && (
                    <span className="text-indigo-400 bg-indigo-500/10 px-2.5 py-1 rounded-full border border-indigo-500/20 animate-pulse">
                      {reprocessState.stage}...
                    </span>
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
                      reprocessState.status === 'SUCCESS' ? 'bg-emerald-500' : 
                      'bg-indigo-500'
                    }`} 
                    style={{ width: `${reprocessState.progress}%` }}
                  ></div>
                </div>
              </div>

              {/* Stage Stepper Badges */}
              <div className="grid grid-cols-5 gap-2 pt-2 border-t border-slate-800/80 text-[11px] text-slate-400 text-center font-medium">
                <div className={`p-1.5 rounded-lg border ${['FETCHING_RESUME', 'ENTITY_RESOLUTION', 'UPDATING_FTS', 'GENERATING_VECTORS', 'LOGGING_TIMELINE', 'COMPLETED'].indexOf(reprocessState.stage) >= 0 ? 'bg-indigo-950/50 border-indigo-500/40 text-indigo-300' : 'bg-slate-900 border-slate-800'}`}>
                  1. Profile
                </div>
                <div className={`p-1.5 rounded-lg border ${['ENTITY_RESOLUTION', 'UPDATING_FTS', 'GENERATING_VECTORS', 'LOGGING_TIMELINE', 'COMPLETED'].indexOf(reprocessState.stage) >= 0 ? 'bg-indigo-950/50 border-indigo-500/40 text-indigo-300' : 'bg-slate-900 border-slate-800'}`}>
                  2. Entities
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

    </div>
  );
}

export default CandidateList;
