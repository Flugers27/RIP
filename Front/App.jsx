import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import Home from './pages/Home';
import MemoryPage from './pages/MemoryPage';
import PrivatePage from './pages/PrivatePage';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/page/:id" element={<MemoryPage />} />
        <Route path="/private/:token" element={<PrivatePage />} />
      </Routes>
    </Router>
  );
}

export default App;
