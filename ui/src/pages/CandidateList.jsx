import { useState, useEffect } from 'react';
import { Search, MapPin, Briefcase, ChevronRight, User, Upload, CheckCircle2, AlertCircle, RefreshCw, MoreVertical } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

function CandidateList() {
  const navigate = useNavigate();
  const [candidates, setCandidates] = useState([]);
  const [query, setQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [openMenuId, setOpenMenuId] = useState(null);
  
  // Upload Manager State
  const [showUploadManager, setShowUploadManager] = useState(false);
  const [uploadQueue, setUploadQueue] = useState([]);

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
        if (data && data.results) {
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
      })
      .catch((err) => console.error(err));
  };

  const toggleMenu = (e, id) => {
    e.stopPropagation();
    setOpenMenuId(openMenuId === id ? null : id);
  };

  const handleReprocess = async (e, id) => {
    e.stopPropagation();
    setOpenMenuId(null);
    try {
      await fetch(`/api/candidates/${id}/reprocess`, { method: 'POST' });
      alert('Reprocessing triggered!');
      fetchCandidates();
    } catch (err) {
      console.error("Failed to reprocess:", err);
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
                    <div className="absolute right-0 top-8 w-40 bg-slate-900 border border-slate-700 rounded-xl shadow-xl overflow-hidden z-10" onClick={(e) => e.stopPropagation()}>
                      <button 
                        onClick={(e) => { e.stopPropagation(); navigate(`/candidate/${candidate.id}`); }}
                        className="w-full text-left px-4 py-2 text-sm text-slate-300 hover:bg-slate-800 hover:text-slate-100 transition-colors"
                      >
                        View Details
                      </button>
                      <button 
                        onClick={(e) => handleReprocess(e, candidate.id)}
                        className="w-full text-left px-4 py-2 text-sm text-slate-300 hover:bg-slate-800 hover:text-slate-100 transition-colors"
                      >
                        Re-process Data
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
