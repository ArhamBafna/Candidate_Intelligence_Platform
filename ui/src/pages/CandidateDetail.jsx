import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, RefreshCw, CheckCircle2, User, Mail, Phone, Briefcase, MapPin, Download, FileText, AlertCircle, Clock } from 'lucide-react';

function CandidateDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [candidate, setCandidate] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState('saved'); // 'saved', 'saving', 'typing', 'error'
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
        setSaveStatus('saved');
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
    setSaveStatus('typing');
    
    // Debounce save (restart timer on every edit)
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }
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
    <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100">
      {/* Header */}
      <header className="px-6 py-4 border-b border-slate-800 bg-slate-900 flex justify-between items-center z-10">
        <div className="flex items-center gap-4">
          <button 
            onClick={() => navigate('/')}
            className="p-2 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-slate-200 transition-colors"
            title="Back to Candidates"
          >
            <ArrowLeft size={20} />
          </button>
          <div>
            <h1 className="text-xl font-bold text-slate-100">{candidate.first_name} {candidate.last_name}</h1>
            <p className="text-sm text-slate-400">{candidate.current_title || 'Candidate Profile'}</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <a
            href={`/api/candidates/${id}/file`}
            download
            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-xl text-sm font-medium transition-colors shadow-lg shadow-indigo-900/20"
          >
            <Download size={16} /> Download Resume
          </a>
          <button 
            onClick={handleReprocess}
            className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-slate-200 px-4 py-2 rounded-xl text-sm font-medium transition-colors border border-slate-700"
          >
            <RefreshCw size={16} /> Re-process Data
          </button>
        </div>
      </header>

      {/* Top Save Status Bar */}
      <div className={`px-6 py-2.5 border-b text-xs font-medium transition-colors ${
        saveStatus === 'saving' ? 'bg-indigo-950/80 border-indigo-800/80 text-indigo-300' :
        saveStatus === 'typing' ? 'bg-amber-950/80 border-amber-800/80 text-amber-300' :
        saveStatus === 'error' ? 'bg-red-950/80 border-red-800/80 text-red-300' :
        'bg-emerald-950/60 border-emerald-900/50 text-emerald-300'
      }`}>
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            {saveStatus === 'saving' && (
              <>
                <RefreshCw size={14} className="animate-spin text-indigo-400" />
                <span>Saving changes...</span>
              </>
            )}
            {saveStatus === 'typing' && (
              <>
                <Clock size={14} className="text-amber-400" />
                <span>Unsaved changes (saving shortly...)</span>
              </>
            )}
            {saveStatus === 'error' && (
              <>
                <AlertCircle size={14} className="text-red-400" />
                <span>Save failed - failed to update profile</span>
              </>
            )}
            {saveStatus === 'saved' && (
              <>
                <CheckCircle2 size={14} className="text-emerald-400" />
                <span>All changes saved</span>
              </>
            )}
          </div>
          <span className="text-slate-400/80 text-[11px]">Real-time Status Bar</span>
        </div>
      </div>

      {/* Main Workspace */}
      <div className="flex-1 overflow-y-auto p-8">
        <div className="max-w-4xl mx-auto space-y-6">
          
          {/* Download Resume Quick Access Card */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-indigo-950/80 border border-indigo-500/30 rounded-xl text-indigo-400">
                <FileText size={24} />
              </div>
              <div>
                <h3 className="font-semibold text-slate-100">Original Resume Document</h3>
                <p className="text-xs text-slate-400">Download the uploaded resume file directly to your device</p>
              </div>
            </div>
            <a
              href={`/api/candidates/${id}/file`}
              download
              className="bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-2.5 rounded-xl font-medium text-sm flex items-center gap-2 transition-colors shadow-lg shadow-indigo-900/20"
            >
              <Download size={18} />
              Download Resume
            </a>
          </div>

          {/* Profile Data Card */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-8 shadow-xl">
            <h2 className="text-lg font-semibold text-slate-200 mb-6 flex items-center gap-2 border-b border-slate-800 pb-4">
              <User size={18} className="text-indigo-400" /> Candidate Details & Profile
            </h2>
            
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">First Name</label>
                  <input 
                    type="text" name="first_name" value={formData.first_name} onChange={handleInputChange}
                    className="w-full bg-slate-950 border border-slate-700/80 rounded-xl px-4 py-2.5 text-slate-200 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">Last Name</label>
                  <input 
                    type="text" name="last_name" value={formData.last_name} onChange={handleInputChange}
                    className="w-full bg-slate-950 border border-slate-700/80 rounded-xl px-4 py-2.5 text-slate-200 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="flex items-center gap-1.5 text-xs font-medium text-slate-400 mb-1.5"><Mail size={14}/> Email Address</label>
                  <input 
                    type="email" name="primary_email" value={formData.primary_email} onChange={handleInputChange}
                    className="w-full bg-slate-950 border border-slate-700/80 rounded-xl px-4 py-2.5 text-slate-200 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all"
                  />
                </div>
                <div>
                  <label className="flex items-center gap-1.5 text-xs font-medium text-slate-400 mb-1.5"><Phone size={14}/> Phone Number</label>
                  <input 
                    type="text" name="primary_phone" value={formData.primary_phone} onChange={handleInputChange}
                    className="w-full bg-slate-950 border border-slate-700/80 rounded-xl px-4 py-2.5 text-slate-200 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="flex items-center gap-1.5 text-xs font-medium text-slate-400 mb-1.5"><Briefcase size={14}/> Current Title</label>
                  <input 
                    type="text" name="current_title" value={formData.current_title} onChange={handleInputChange}
                    className="w-full bg-slate-950 border border-slate-700/80 rounded-xl px-4 py-2.5 text-slate-200 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">Current Company</label>
                  <input 
                    type="text" name="current_company" value={formData.current_company} onChange={handleInputChange}
                    className="w-full bg-slate-950 border border-slate-700/80 rounded-xl px-4 py-2.5 text-slate-200 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="flex items-center gap-1.5 text-xs font-medium text-slate-400 mb-1.5"><MapPin size={14}/> City / Location</label>
                  <input 
                    type="text" name="current_city" value={formData.current_city} onChange={handleInputChange}
                    className="w-full bg-slate-950 border border-slate-700/80 rounded-xl px-4 py-2.5 text-slate-200 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">Availability Status</label>
                  <select 
                    name="availability_status" value={formData.availability_status} onChange={handleInputChange}
                    className="w-full bg-slate-950 border border-slate-700/80 rounded-xl px-4 py-2.5 text-slate-200 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all"
                  >
                    <option value="ACTIVE">ACTIVE</option>
                    <option value="PLACED">PLACED</option>
                    <option value="INACTIVE">INACTIVE</option>
                    <option value="DNC">DNC</option>
                  </select>
                </div>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}

export default CandidateDetail;

