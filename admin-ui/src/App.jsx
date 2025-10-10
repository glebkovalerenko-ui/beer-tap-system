// src/App.jsx
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import GuestsPage from './pages/GuestsPage';
import TapsPage from './pages/TapsPage';
import DashboardPage from './pages/DashboardPage';
import './App.css'; // Подключаем наши будущие стили

function App() {
  return (
    <Router>
      <div className="app-container">
        <nav className="sidebar">
          <h3>Бар-Система</h3>
          <ul>
            <li><Link to="/">Главная</Link></li>
            <li><Link to="/guests">Гости</Link></li>
            <li><Link to="/taps">Краны</Link></li>
          </ul>
        </nav>
        <main className="content">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/guests" element={<GuestsPage />} />
            <Route path="/taps" element={<TapsPage />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}
export default App;