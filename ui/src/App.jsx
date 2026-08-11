import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import CandidateList from './pages/CandidateList';
import CandidateDetail from './pages/CandidateDetail';
import './App.css';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<CandidateList />} />
        <Route path="/candidate/:id" element={<CandidateDetail />} />
      </Routes>
    </Router>
  );
}

export default App;
