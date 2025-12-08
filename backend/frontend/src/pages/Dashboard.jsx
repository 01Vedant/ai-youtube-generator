/**
 * Dashboard Page - Main hub for project management
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../services/api';
import ProjectCard from '../components/ProjectCard';
import NewProjectModal from '../components/NewProjectModal';
import CreateStoryModal from '../components/CreateStoryModal';
import '../styles/Dashboard.css';

function Dashboard() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showNewProjectModal, setShowNewProjectModal] = useState(false);
  const [showCreateStoryModal, setShowCreateStoryModal] = useState(false);
  const [lastJob, setLastJob] = useState(null);
  const [stats, setStats] = useState(null);

  useEffect(() => {
    fetchProjects();
    fetchStats();
  }, []);

  const fetchProjects = async () => {
    try {
      const response = await apiClient.get('/projects', {
        params: { limit: 20, offset: 0 }
      });
      setProjects(response.data.projects);
    } catch (error) {
      console.error('Failed to fetch projects:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await apiClient.get('/stats');
      setStats(response.data);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  };

  const handleCreateProject = async (projectData) => {
    try {
      const response = await apiClient.post('/projects/create', projectData);
      setShowNewProjectModal(false);
      navigate(`/project/${response.data.project_id}`);
    } catch (error) {
      console.error('Failed to create project:', error);
      alert('Failed to create project. Please try again.');
    }
  };

  const handleDeleteProject = async (projectId) => {
    if (!window.confirm('Are you sure you want to delete this project?')) return;
    
    try {
      await apiClient.delete(`/projects/${projectId}`);
      setProjects(projects.filter(p => p.project_id !== projectId));
    } catch (error) {
      console.error('Failed to delete project:', error);
      alert('Failed to delete project.');
    }
  };

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <div className="header-content">
          <h1>DevotionalAI Studio</h1>
          <p>Create beautiful devotional videos with AI</p>
        </div>
        <div className="header-buttons">
          <button 
            className="btn btn-primary btn-lg"
            onClick={() => setShowCreateStoryModal(true)}
            aria-label="Create Story"
          >
            ✨ Create Story
          </button>
          <button 
            className="btn btn-secondary btn-lg"
            onClick={() => setShowNewProjectModal(true)}
          >
            + New Project
          </button>
        </div>
      </div>

      {stats && (
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-number">{stats.total_projects}</div>
            <div className="stat-label">Projects</div>
          </div>
          <div className="stat-card">
            <div className="stat-number">{stats.videos_generated}</div>
            <div className="stat-label">Videos Created</div>
          </div>
          <div className="stat-card">
            <div className="stat-number">{stats.storage_used_gb.toFixed(1)} GB</div>
            <div className="stat-label">Storage Used</div>
          </div>
        </div>
      )}

      <div className="projects-section">
        <h2>Your Projects</h2>
        
        {loading ? (
          <div className="loading">Loading projects...</div>
        ) : projects.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">🎬</div>
            <h3>No projects yet</h3>
            <p>Create your first devotional video project to get started</p>
            <button 
              className="btn btn-primary"
              onClick={() => setShowNewProjectModal(true)}
            >
              Create First Project
            </button>
          </div>
        ) : (
          <div className="projects-grid">
            {projects.map(project => (
              <ProjectCard
                key={project.project_id}
                project={project}
                onEdit={() => navigate(`/project/${project.project_id}`)}
                onStudio={() => navigate(`/studio/${project.project_id}`)}
                onDelete={() => handleDeleteProject(project.project_id)}
              />
            ))}
          </div>
        )}
      </div>

      {showNewProjectModal && (
        <NewProjectModal
          onCreate={handleCreateProject}
          onClose={() => setShowNewProjectModal(false)}
        />
      )}

      {showCreateStoryModal && (
        <CreateStoryModal
          open={showCreateStoryModal}
          onClose={() => setShowCreateStoryModal(false)}
          onSubmitted={(job) => {
            setLastJob(job);
            setShowCreateStoryModal(false);
            // optionally navigate to /create-story to see full progress
            navigate('/create-story', { state: { job } });
          }}
        />
      )}
    </div>
  );
}

export default Dashboard;
