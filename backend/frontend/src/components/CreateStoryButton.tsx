import React from 'react';
import { useNavigate } from 'react-router-dom';

// ensure top CTA has a unique testid the smoke test can target
export default function CreateStoryButton(): JSX.Element {
  const navigate = useNavigate();
  return (
    <button
      data-testid="create-story-top"
      className="rounded bg-blue-600 px-4 py-2 text-white"
      onClick={() => navigate('/create?e2e=1')}
    >
      Create Story
    </button>
  );
}
