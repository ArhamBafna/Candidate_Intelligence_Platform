import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, RefreshCw, CheckCircle2, User, Mail, Phone, Briefcase, MapPin, Download, FileText, AlertCircle, Clock, Trash2, Sparkles } from 'lucide-react';

function CandidateDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [candidate, setCandidate] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState('saved'); // 'saved', 'saving', 'typing', 'error'
  const [lastSavedTime, setLastSavedTime] = useState(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const saveTimeoutRef = useRef(null);

  // Reprocess Manager State
  const [reprocessState, setReprocessState] = useState(null);

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
        setLastSavedTime(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
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
    const candidateName = candidate ? `${candidate.first_name} ${candidate.last_name}` : 'Candidate';
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
                  stage_detail: event.stage_detail || prev.stage_detail,
                  status: event.status,
                  progress: event.progress,
                  message: event.message,
                  used_ai: event.used_ai ?? prev.used_ai,
                  model_name: event.model_name || prev.model_name,
                  used_ai_fallback: event.used_ai_fallback ?? prev.used_ai_fallback,
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

  const handleDeleteCandidate = async () => {
    setIsDeleting(true);
    try {
      const res = await fetch(`/api/candidates/${id}`, { method: 'DELETE' });
      if (res.ok || res.status === 204) {
        navigate('/');
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
          <button 
            onClick={() => setShowDeleteModal(true)}
            className="flex items-center gap-2 bg-red-600/10 hover:bg-red-600/20 text-red-400 border border-red-500/20 px-4 py-2 rounded-xl text-sm font-medium transition-colors"
          >
            <Trash2 size={16} /> Delete Candidate
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
                <span>All changes saved {lastSavedTime && `(Last saved at ${lastSavedTime})`}</span>
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

      {/* Delete Confirmation Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-[70]">
          <div className="bg-slate-900 border border-slate-700 max-w-md w-full rounded-2xl p-6 relative shadow-2xl">
            <div className="flex items-center gap-3 text-red-400 mb-4">
              <div className="p-2 bg-red-500/10 rounded-xl border border-red-500/20">
                <Trash2 size={24} />
              </div>
              <h3 className="text-lg font-bold text-slate-100">Delete Candidate</h3>
            </div>
            
            <p className="text-slate-300 text-sm mb-2">
              Are you sure you want to delete <span className="font-semibold text-slate-100">{candidate.first_name} {candidate.last_name}</span>?
            </p>
            <p className="text-slate-400 text-xs mb-6">
              This action will permanently remove candidate details, timeline events, and search index vectors.
            </p>
            
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowDeleteModal(false)}
                disabled={isDeleting}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium rounded-xl transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteCandidate}
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
                  fetchCandidate();
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

    </div>
  );
}

export default CandidateDetail;

