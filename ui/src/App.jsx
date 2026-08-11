import { useState, useEffect } from 'react';
import { Search, MapPin, Briefcase, ChevronRight, User } from 'lucide-react';

function App() {
  const [candidates, setCandidates] = useState([]);
  const [query, setQuery] = useState('');

  // Fetch initial candidates
  useEffect(() => {
    fetch('/api/candidates')
      .then((res) => res.json())
      .then((data) => {
        if (Array.isArray(data)) {
          setCandidates(data);
        }
      })
      .catch((err) => console.error(err));
  }, []);

  const handleSearch = (e) => {
    e.preventDefault();
    fetch('/api/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query_text: query, top_k: 10 })
    })
      .then((res) => res.json())
      .then((data) => {
        // Just mock mapping back to UI for now
        console.log('Search Results:', data);
      })
      .catch((err) => console.error(err));
  };

  return (
    <div className="min-h-screen p-8 max-w-7xl mx-auto flex flex-col gap-8">
      <header className="flex justify-between items-center mb-4">
        <div>
          <h1 className="text-3xl font-bold gradient-text tracking-tight">Candidate Intelligence Platform</h1>
          <p className="text-slate-400 mt-1">Local-first, zero-cost recruitment automation.</p>
        </div>
      </header>

      {/* Search Bar */}
      <section className="glass-panel p-6 rounded-2xl">
        <form onSubmit={handleSearch} className="flex gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-4 top-3.5 h-5 w-5 text-slate-500" />
            <input 
              type="text" 
              placeholder="Search candidates by skills, location, or semantic rationale..." 
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full bg-slate-900/50 border border-slate-700 rounded-xl pl-12 pr-4 py-3 text-slate-200 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
            />
          </div>
          <button type="submit" className="bg-indigo-600 hover:bg-indigo-700 text-white px-8 py-3 rounded-xl font-medium transition-colors shadow-lg shadow-indigo-900/20">
            Search
          </button>
        </form>
      </section>

      {/* Candidate List */}
      <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {candidates.map((candidate) => (
          <div key={candidate.id} className="glass-panel p-6 rounded-2xl hover:border-slate-600 transition-all cursor-pointer group">
            <div className="flex justify-between items-start mb-4">
              <div className="flex items-center gap-3">
                <div className="bg-slate-700/50 p-3 rounded-full text-indigo-400">
                  <User size={20} />
                </div>
                <div>
                  <h3 className="font-semibold text-lg text-slate-100 group-hover:text-indigo-300 transition-colors">
                    {candidate.first_name} {candidate.last_name}
                  </h3>
                  <span className={`text-xs px-2 py-1 rounded-full font-medium ${
                    candidate.availability_status === 'ACTIVE' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 
                    'bg-slate-700 text-slate-300 border border-slate-600'
                  }`}>
                    {candidate.availability_status}
                  </span>
                </div>
              </div>
            </div>
            
            <div className="space-y-3 mt-6 text-sm text-slate-400">
              {candidate.current_title && (
                <div className="flex items-center gap-2">
                  <Briefcase size={16} className="text-slate-500" />
                  <span>{candidate.current_title} at {candidate.current_company || 'Unknown'}</span>
                </div>
              )}
              {candidate.current_city && (
                <div className="flex items-center gap-2">
                  <MapPin size={16} className="text-slate-500" />
                  <span>{candidate.current_city}, {candidate.current_country}</span>
                </div>
              )}
            </div>
            
            <div className="mt-6 pt-4 border-t border-slate-700/50 flex justify-end">
              <button className="flex items-center gap-1 text-sm text-indigo-400 hover:text-indigo-300 font-medium">
                View Profile <ChevronRight size={16} />
              </button>
            </div>
          </div>
        ))}
        
        {candidates.length === 0 && (
          <div className="col-span-full py-12 text-center text-slate-500 border-2 border-dashed border-slate-700 rounded-2xl">
            No candidates ingested yet. Connect to the CAS datastore to begin.
          </div>
        )}
      </section>
    </div>
  );
}

export default App;
