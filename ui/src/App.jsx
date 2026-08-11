import { useState, useEffect } from 'react';
import { Search, MapPin, Briefcase, ChevronRight, User, X, Clock, Award, Upload } from 'lucide-react';

function App() {
  const [candidates, setCandidates] = useState([]);
  const [query, setQuery] = useState('');
  const [selectedCandidate, setSelectedCandidate] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

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

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    fetch('/api/candidates/upload', {
      method: 'POST',
      body: formData
    })
      .then((res) => res.json())
      .then((data) => {
        setIsUploading(false);
        if (data.status === 'success') {
          fetchCandidates();
        }
      })
      .catch((err) => {
        console.error(err);
        setIsUploading(false);
      });
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

  const handleSelectCandidate = (candidate) => {
    setSelectedCandidate(candidate);
    fetch(`/api/candidates/${candidate.id}/timeline`)
      .then((res) => res.json())
      .then((data) => {
        if (Array.isArray(data)) {
          setTimeline(data);
        } else {
          setTimeline([]);
        }
      })
      .catch(() => setTimeline([]));
  };

  return (
    <div className="min-h-screen p-8 max-w-7xl mx-auto flex flex-col gap-8">
      {/* Header */}
      <header className="flex justify-between items-center mb-2">
        <div>
          <h1 className="text-3xl font-bold gradient-text tracking-tight">Candidate Intelligence Platform</h1>
          <p className="text-slate-400 mt-1">Local-first, zero-cloud candidate retrieval & CRM platform.</p>
        </div>
        <div className="flex items-center gap-3">
          <label className="bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-2.5 rounded-xl font-medium cursor-pointer transition-colors shadow-lg shadow-indigo-900/20 flex items-center gap-2 text-sm">
            <Upload size={18} />
            <span>{isUploading ? 'Ingesting...' : 'Upload Resume'}</span>
            <input type="file" accept=".pdf,.docx,.doc,.txt" className="hidden" onChange={handleFileUpload} disabled={isUploading} />
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
            onClick={() => handleSelectCandidate(candidate)}
            className="glass-panel p-6 rounded-2xl hover:border-indigo-500/50 transition-all cursor-pointer group flex flex-col justify-between"
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
                {candidate.rrf_score !== undefined && (
                  <span className="text-xs font-mono bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 px-2 py-1 rounded">
                    Rank #{candidate.rank}
                  </span>
                )}
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
                View Details <ChevronRight size={16} />
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

      {/* Candidate Profile Modal */}
      {selectedCandidate && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="glass-panel border-slate-700 max-w-2xl w-full rounded-2xl p-6 relative max-h-[90vh] overflow-y-auto">
            <button 
              onClick={() => setSelectedCandidate(null)}
              className="absolute top-4 right-4 text-slate-400 hover:text-slate-200 p-1 rounded-lg hover:bg-slate-800"
            >
              <X size={20} />
            </button>

            <div className="flex items-start gap-4 mb-6">
              <div className="bg-indigo-950 border border-indigo-500/30 p-4 rounded-xl text-indigo-400">
                <User size={32} />
              </div>
              <div>
                <h2 className="text-2xl font-bold text-slate-100">
                  {selectedCandidate.first_name} {selectedCandidate.last_name}
                </h2>
                <p className="text-slate-400 text-sm mt-0.5">
                  {selectedCandidate.current_title || 'Candidate'} {selectedCandidate.current_company ? `at ${selectedCandidate.current_company}` : ''}
                </p>
                <div className="flex gap-2 mt-2">
                  <span className="text-xs px-2.5 py-1 rounded-full font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    {selectedCandidate.availability_status}
                  </span>
                  {selectedCandidate.current_city && (
                    <span className="text-xs px-2.5 py-1 rounded-full font-medium bg-slate-800 text-slate-300 border border-slate-700 flex items-center gap-1">
                      <MapPin size={12} /> {selectedCandidate.current_city}
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Timeline Section */}
            <div className="border-t border-slate-700/60 pt-6">
              <h3 className="text-lg font-semibold text-slate-200 mb-4 flex items-center gap-2">
                <Clock size={18} className="text-indigo-400" />
                Candidate Timeline
              </h3>
              {timeline.length > 0 ? (
                <div className="space-y-4">
                  {timeline.map((evt) => (
                    <div key={evt.id} className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl flex gap-3">
                      <div className="bg-indigo-500/10 text-indigo-400 p-2 rounded-lg h-fit mt-0.5">
                        <Award size={16} />
                      </div>
                      <div>
                        <div className="flex justify-between items-center">
                          <h4 className="font-medium text-slate-200 text-sm">{evt.title}</h4>
                          <span className="text-xs text-slate-500">{new Date(evt.created_at || Date.now()).toLocaleDateString()}</span>
                        </div>
                        <p className="text-xs text-slate-400 mt-1">{evt.description || `Status updated by ${evt.created_by}`}</p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-500 italic bg-slate-900/40 p-4 rounded-xl text-center border border-slate-800/60">
                  No timeline events logged yet for this candidate.
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
