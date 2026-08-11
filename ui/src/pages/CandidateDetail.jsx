import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, RefreshCw, CheckCircle2, User, Mail, Phone, Briefcase, MapPin } from 'lucide-react';

function CandidateDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [candidate, setCandidate] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState(''); // 'saved', 'saving', 'error'
  const saveTimeoutRef = useRef(null);

  // Form state
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    primary_email: '',
    primary_phone: '',
    current_title: '',
    current_company: '',
    current_city: '',
    availability_status: ''
  });

  const fetchCandidate = useCallback(async () => {
    try {
      const res = await fetch(`/api/candidates/${id}`);
      if (res.ok) {
        const data = await res.json();
        setCandidate(data);
        setFormData({
          first_name: data.first_name || '',
          last_name: data.last_name || '',
          primary_email: data.primary_email || '',
          primary_phone: data.primary_phone || '',
          current_title: data.current_title || '',
          current_company: data.current_company || '',
          current_city: data.current_city || '',
          availability_status: data.availability_status || 'ACTIVE'
        });
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchCandidate();
  }, [fetchCandidate]);

  const saveChanges = async (newData) => {
    setSaving(true);
    setSaveStatus('saving');
    try {
      const res = await fetch(`/api/candidates/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newData)
      });
      if (res.ok) {
        setSaveStatus('saved');
        setTimeout(() => setSaveStatus(''), 2000);
      } else {
        setSaveStatus('error');
      }
    } catch (err) {
      console.error("Save failed:", err);
      setSaveStatus('error');
    } finally {
      setSaving(false);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    const newData = { ...formData, [name]: value };
    setFormData(newData);
    
    // Debounce save (restart timer on every edit)
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }
    setSaveStatus('typing...');
    saveTimeoutRef.current = setTimeout(() => {
      saveChanges(newData);
    }, 1000); // Auto-save 1 second after last edit
  };

  const handleReprocess = async () => {
    try {
      await fetch(`/api/candidates/${id}/reprocess`, { method: 'POST' });
      alert('Reprocessing triggered!');
    } catch (err) {
      console.error(err);
    }
  };

  if (loading) {
    return <div className="p-8 text-slate-400">Loading candidate profile...</div>;
  }

  if (!candidate) {
    return <div className="p-8 text-red-400">Candidate not found.</div>;
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="px-6 py-4 border-b border-slate-700/50 bg-slate-900/50 flex justify-between items-center z-10">
        <div className="flex items-center gap-4">
          <button 
            onClick={() => navigate('/')}
            className="p-2 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-slate-200 transition-colors"
          >
            <ArrowLeft size={20} />
          </button>
          <div>
            <h1 className="text-xl font-bold text-slate-100">{candidate.first_name} {candidate.last_name}</h1>
            <p className="text-sm text-slate-400">{candidate.current_title}</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-sm font-medium">
            {saveStatus === 'typing...' && <span className="text-slate-400">Typing...</span>}
            {saveStatus === 'saving' && <span className="text-indigo-400 animate-pulse">Saving...</span>}
            {saveStatus === 'saved' && <span className="text-emerald-400 flex items-center gap-1"><CheckCircle2 size={14} /> Saved</span>}
            {saveStatus === 'error' && <span className="text-red-400">Save failed</span>}
          </div>
          <button 
            onClick={handleReprocess}
            className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-slate-200 px-4 py-2 rounded-xl text-sm font-medium transition-colors border border-slate-700"
          >
            <RefreshCw size={16} /> Re-process Data
          </button>
        </div>
      </header>

      {/* Split Screen Workspace */}
      <div className="flex-1 flex overflow-hidden">
        
        {/* Left Pane: PDF Viewer */}
        <div className="w-1/2 border-r border-slate-700/50 bg-slate-950 flex flex-col">
          <div className="p-3 bg-slate-900 border-b border-slate-800 text-sm font-medium text-slate-400 flex justify-between items-center">
            <span>Original Document</span>
            <a href={`/api/candidates/${id}/file`} target="_blank" rel="noreferrer" className="text-indigo-400 hover:text-indigo-300">Open in new tab</a>
          </div>
          <div className="flex-1 w-full bg-slate-800/50 p-4">
            <iframe 
              src={`/api/candidates/${id}/file`} 
              className="w-full h-full rounded-lg border border-slate-700 shadow-xl bg-white"
              title="Resume PDF"
            />
          </div>
        </div>

        {/* Right Pane: Editable Data */}
        <div className="w-1/2 bg-slate-900 overflow-y-auto p-8">
          <h2 className="text-lg font-semibold text-slate-200 mb-6 flex items-center gap-2">
            <User size={18} className="text-indigo-400" /> Candidate Profile
          </h2>
          
          <div className="space-y-6 max-w-xl">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">First Name</label>
                <input 
                  type="text" name="first_name" value={formData.first_name} onChange={handleInputChange}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Last Name</label>
                <input 
                  type="text" name="last_name" value={formData.last_name} onChange={handleInputChange}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="flex items-center gap-1 text-xs font-medium text-slate-400 mb-1"><Mail size={12}/> Email</label>
                <input 
                  type="email" name="primary_email" value={formData.primary_email} onChange={handleInputChange}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="flex items-center gap-1 text-xs font-medium text-slate-400 mb-1"><Phone size={12}/> Phone</label>
                <input 
                  type="text" name="primary_phone" value={formData.primary_phone} onChange={handleInputChange}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>

            <div>
              <label className="flex items-center gap-1 text-xs font-medium text-slate-400 mb-1"><Briefcase size={12}/> Current Title</label>
              <input 
                type="text" name="current_title" value={formData.current_title} onChange={handleInputChange}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Current Company</label>
              <input 
                type="text" name="current_company" value={formData.current_company} onChange={handleInputChange}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="flex items-center gap-1 text-xs font-medium text-slate-400 mb-1"><MapPin size={12}/> City/Location</label>
                <input 
                  type="text" name="current_city" value={formData.current_city} onChange={handleInputChange}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Status</label>
                <select 
                  name="availability_status" value={formData.availability_status} onChange={handleInputChange}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500"
                >
                  <option value="ACTIVE">ACTIVE</option>
                  <option value="PLACED">PLACED</option>
                  <option value="INACTIVE">INACTIVE</option>
                  <option value="DNC">DNC</option>
                </select>
              </div>
            </div>
            
            <p className="text-xs text-slate-500 mt-8 flex items-center gap-2">
              Changes are saved automatically as you type.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default CandidateDetail;
