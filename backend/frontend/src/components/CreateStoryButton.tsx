import React from 'react';
import { useNavigate } from 'react-router-dom';

export const TID = {
  createTop: 'create-story-top',
  create: 'create-story',
  modal: 'create-story-modal',
  title: 'title-input',
  desc: 'description-input',
  full: 'fulltext-input',
  submit: 'submit-create',
  thumb: 'thumbnail',
} as const;

// ensure top CTA has a unique testid the smoke test can target
export default function CreateStoryButton(): JSX.Element {
  const navigate = useNavigate();
  return (
    <button
      data-testid="create-story"
      className="rounded bg-blue-600 px-4 py-2 text-white"
      onClick={() => navigate('/create?e2e=1')}
    >
      Create Story
    </button>
  );
}

