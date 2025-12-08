<#
ffmpeg_stitcher.ps1

PowerShell script that assembles per-scene high-res image + audio + subtitles
into scene clips and concatenates them into a final 4K MP4 using ffmpeg.

Requirements:
 - ffmpeg installed and on PATH
 - assets/images/scene_{n}.png (4K recommended)
 - assets/audio/scene_{n}.mp3
 - assets/subtitles/scene_{n}.srt
 - assets/assets_map.json

Usage:
  Open PowerShell, run:
    .\scripts\ffmpeg_stitcher.ps1

This script creates `output/scene_{n}_final.mp4` and `output/Prahlad_Final_4K.mp4`.
#>

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Assets = Join-Path $ProjectRoot '..\assets' | Resolve-Path -Relative
$Out = Join-Path $ProjectRoot '..\output' | Resolve-Path -Relative
If (-Not (Test-Path $Out)) { New-Item -ItemType Directory -Path $Out | Out-Null }

$mapPath = Join-Path $Assets 'assets_map.json'
if (-Not (Test-Path $mapPath)) { Write-Host 'Missing assets_map.json. Run run_pipeline.py first.'; exit 1 }

$map = Get-Content $mapPath -Raw | ConvertFrom-Json

$concatList = Join-Path $Out 'concat_list.txt'
if (Test-Path $concatList) { Remove-Item $concatList }

foreach ($item in $map) {
    $idx = $item.scene
    $img = Join-Path $Assets "images\scene_${idx}.png"
    $audio = Join-Path $Assets "audio\scene_${idx}.mp3"
    $srt = Join-Path $Assets "subtitles\scene_${idx}.srt"
    $sceneOut = Join-Path $Out "scene_${idx}_final.mp4"

    if (-Not (Test-Path $img)) { Write-Host "Image missing for scene $idx: $img. Skipping or use a placeholder." }

    # Create a zoom+pan effect from single image using ffmpeg zoompan filter
    # Use a slow linear zoom from 1.0 to 1.04 over the audio duration
    $dur = $item.duration_seconds
    if (-Not $dur) { $dur = 8 }

    # Build filter: scale to at least 3840x2160 then zoompan
    $filter = "[0:v]scale=3840:2160:force_original_aspect_ratio=decrease,pad=3840:2160:(ow-iw)/2:(oh-ih)/2,zoompan=z='if(lte(on,$($dur*25)),1+0.04*on/($($dur*25)),1)':d=1:fps=25,format=yuv420p[v]"

    # If subtitles file exists, we'll burn them in during mapping
    if (Test-Path $srt) {
        # create video from image and attach audio, then burn subtitles
        $tmp = Join-Path $Out "scene_${idx}_tmp.mp4"
        ffmpeg -y -loop 1 -i $img -i $audio -filter_complex $filter -map "[v]" -map 1:a -c:v libx264 -c:a aac -b:v 40M -shortest $tmp
        ffmpeg -y -i $tmp -vf "subtitles=${srt}" -c:v libx264 -c:a copy -b:v 40M $sceneOut
        Remove-Item $tmp
    } else {
        # no subtitles: directly create final scene clip
        ffmpeg -y -loop 1 -i $img -i $audio -filter_complex $filter -map "[v]" -map 1:a -c:v libx264 -c:a aac -b:v 40M -shortest $sceneOut
    }

    Add-Content -Path $concatList -Value "file '$(Resolve-Path $sceneOut)'"
}

# Concatenate all scene clips
ffmpeg -y -f concat -safe 0 -i $concatList -c copy (Join-Path $Out 'Prahlad_Final_4K.mp4')
Write-Host 'Final video written to output\Prahlad_Final_4K.mp4'
