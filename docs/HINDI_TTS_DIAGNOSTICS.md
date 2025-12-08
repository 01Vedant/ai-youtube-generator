# Browser Console Diagnostics for Hindi TTS Status Page

Run this code in the browser console on `http://localhost:5173/render/<job_id>`:

```javascript
// Hindi TTS Diagnostics Snippet
// Run this in the browser console on /render/<job_id> page

(async function hindiTtsDiagnostics() {
  console.log('=== Hindi TTS Diagnostics ===\n');
  
  // Extract job ID from URL
  const jobId = window.location.pathname.split('/render/')[1];
  if (!jobId) {
    console.error('❌ No job ID found in URL');
    return;
  }
  
  console.log(`Job ID: ${jobId}\n`);
  
  // Fetch job status
  console.log('1️⃣ Fetching job status...');
  try {
    const statusResponse = await fetch(`http://127.0.0.1:8000/render/${jobId}/status`);
    console.log(`Status: ${statusResponse.status} ${statusResponse.statusText}`);
    
    if (!statusResponse.ok) {
      console.error(`❌ Status fetch failed with ${statusResponse.status}`);
      return;
    }
    
    const statusData = await statusResponse.json();
    console.log('✅ Job Status JSON:', statusData);
    console.log('\n');
    
    // Check audio metadata
    console.log('2️⃣ Checking audio metadata...');
    if (statusData.audio) {
      console.log('✅ Audio metadata exists:');
      console.log(`   - lang: ${statusData.audio.lang || 'N/A'}`);
      console.log(`   - voice_id: ${statusData.audio.voice_id || 'N/A'}`);
      console.log(`   - provider: ${statusData.audio.provider || 'N/A'}`);
      console.log(`   - paced: ${statusData.audio.paced !== undefined ? statusData.audio.paced : 'N/A'}`);
      console.log(`   - total_duration_sec: ${statusData.audio.total_duration_sec || 'N/A'}`);
      console.log('   Full audio object:', statusData.audio);
    } else {
      console.warn('⚠️  No audio metadata found in status response');
    }
    console.log('\n');
    
    // HEAD check final video
    console.log('3️⃣ HEAD check final video...');
    if (statusData.final_video_url) {
      const videoUrl = statusData.final_video_url.startsWith('http') 
        ? statusData.final_video_url 
        : `http://127.0.0.1:8000${statusData.final_video_url}`;
      
      console.log(`Video URL: ${videoUrl}`);
      
      try {
        const videoResponse = await fetch(videoUrl, { method: 'HEAD' });
        console.log(`Video HEAD Status: ${videoResponse.status} ${videoResponse.statusText}`);
        
        const headers = {};
        videoResponse.headers.forEach((value, key) => {
          headers[key] = value;
        });
        
        console.log('Video Headers:', headers);
        console.log(`   - Content-Type: ${headers['content-type'] || 'N/A'}`);
        console.log(`   - Content-Length: ${headers['content-length'] || 'N/A'} bytes`);
        
        if (videoResponse.ok) {
          console.log('✅ Video is accessible');
        } else {
          console.error(`❌ Video HEAD check failed with ${videoResponse.status}`);
        }
      } catch (err) {
        console.error('❌ Video HEAD request failed:', err.message);
      }
    } else {
      console.warn('⚠️  No final_video_url in status response');
    }
    console.log('\n');
    
    // Check UI badges
    console.log('4️⃣ Checking UI badges on page...');
    const badges = document.querySelectorAll('.feature-badge');
    if (badges.length > 0) {
      console.log(`Found ${badges.length} badge(s):`);
      badges.forEach((badge, idx) => {
        console.log(`   Badge ${idx + 1}: ${badge.textContent.trim()}`);
      });
    } else {
      console.warn('⚠️  No badges found with class .feature-badge');
    }
    
    console.log('\n=== Diagnostics Complete ===');
    
    // Return summary object
    return {
      jobId,
      state: statusData.state,
      hasAudio: !!statusData.audio,
      audioLang: statusData.audio?.lang,
      audioVoiceId: statusData.audio?.voice_id,
      audioPaced: statusData.audio?.paced,
      audioProvider: statusData.audio?.provider,
      hasVideo: !!statusData.final_video_url,
      videoUrl: statusData.final_video_url,
      badgeCount: badges.length,
    };
    
  } catch (err) {
    console.error('❌ Error during diagnostics:', err);
    console.error('Stack:', err.stack);
    throw err;
  }
})();
```

## Usage

1. Open the status page: `http://localhost:5173/render/<job_id>`
2. Open browser DevTools (F12)
3. Go to Console tab
4. Paste the entire code block above
5. Press Enter to execute

## What It Checks

- ✅ Extracts job ID from URL
- ✅ Fetches `/render/{id}/status` and logs full JSON
- ✅ Validates audio metadata presence and fields
- ✅ HEAD checks the final video URL
- ✅ Logs video headers (Content-Type, Content-Length)
- ✅ Searches for UI badges on the page
- ✅ Returns summary object for programmatic access

## Example Output

```
=== Hindi TTS Diagnostics ===

Job ID: abc-123-def

1️⃣ Fetching job status...
Status: 200 OK
✅ Job Status JSON: {job_id: "abc-123-def", state: "success", ...}

2️⃣ Checking audio metadata...
✅ Audio metadata exists:
   - lang: hi
   - voice_id: hi-IN-SwaraNeural
   - provider: edge
   - paced: true
   - total_duration_sec: 8.5
   Full audio object: {...}

3️⃣ HEAD check final video...
Video URL: http://127.0.0.1:8000/artifacts/abc-123-def/final_video.mp4
Video HEAD Status: 200 OK
Video Headers: {...}
   - Content-Type: video/mp4
   - Content-Length: 1234567 bytes
✅ Video is accessible

4️⃣ Checking UI badges on page...
Found 3 badge(s):
   Badge 1: 🇮🇳 Hindi • Swara (soothing) • Paced
   Badge 2: 📐 2 Templates
   Badge 3: ⭐ FINAL (1080p)

=== Diagnostics Complete ===
```
