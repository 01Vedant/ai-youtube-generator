import React from 'react';
import { previewImageUrl, previewAudioUrl } from '../services/api';

export default function ScenePreview({ scene }){
  const img = previewImageUrl(scene);
  // Use backend-provided audio when available; otherwise use an embedded silent MP3 data URI
  const audio = previewAudioUrl(scene) || 'data:audio/mp3;base64,SUQzBAAAAAAAI1RTU0UAAAAPAAADTGF2ZjU2LjMyLjEwNAAAAAAAAAAAAAA/77+977+9GQAAAADvv70AAAAAExBTUUzLjkvvv70AAAAAA\nAAAAAAAAA==';

  return (
    <div className="rounded overflow-hidden bg-black/50" style={{ width: 160 }}>
      <img src={img} alt={scene?.scene_title ? `${scene.scene_title} preview` : 'Scene placeholder image'} className="w-full h-28 object-cover" />
      <div className="p-2">
        <div className="text-xs text-white/80 truncate">{scene?.scene_title || 'Untitled'}</div>
        <audio controls className="w-full mt-2" src={audio} preload="none" aria-label={scene?.scene_title ? `${scene.scene_title} audio preview` : 'Scene audio preview'}>
          Your browser does not support the audio element.
        </audio>
      </div>
    </div>
  );
}
