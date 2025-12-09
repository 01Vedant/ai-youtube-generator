import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import CreateStoryModal from './CreateStoryModal';
import '../styles/Sidebar.css';

export default function Sidebar() {
  const location = useLocation();
  const [showCreateStoryModal, setShowCreateStoryModal] = useState(false);

  const isActive = (path) => location.pathname === path;

  const navItems = [
    { label: 'Dashboard', path: '/', icon: '📊' },
    { label: 'Templates', path: '/templates', icon: '📚' },
    { label: 'Settings', path: '/settings', icon: '⚙️' },
  ];

  return (
    <>
      <aside className="sidebar">
        <nav className="sidebar-nav">
          <div className="sidebar-section">
            <h3 className="sidebar-title">Navigation</h3>
            <ul className="nav-list">
              {navItems.map((item) => (
                <li key={item.path}>
                  <Link
                    to={item.path}
                    className={`nav-link ${isActive(item.path) ? 'active' : ''}`}
                  >
                    <span className="nav-icon">{item.icon}</span>
                    <span className="nav-label">{item.label}</span>
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div className="sidebar-section sidebar-actions">
            <h3 className="sidebar-title">Create</h3>
            <button
              className="sidebar-action-btn create-story-btn"
              onClick={() => setShowCreateStoryModal(true)}
              aria-label="Create Story"
              data-testid="create-story"
            >
              <span className="action-icon">✨</span>
              <span className="action-label">Create Story</span>
            </button>
          </div>
        </nav>
      </aside>

      {showCreateStoryModal && (
        <CreateStoryModal
          open={showCreateStoryModal}
          onClose={() => setShowCreateStoryModal(false)}
          onSubmitted={(job) => {
            setShowCreateStoryModal(false);
          }}
        />
      )}
    </>
  );
}
