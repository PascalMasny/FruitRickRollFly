import { useEffect, useRef, useState } from 'react'
import type { Video } from '../lib/types'

interface Props {
  video: Video
  onTime(seconds: number): void
  seekTo: number | null
}

declare global {
  interface Window {
    YT?: {
      Player: new (element: HTMLElement, options: Record<string, unknown>) => YouTubePlayer
      PlayerState: { PLAYING: number }
    }
    onYouTubeIframeAPIReady?: () => void
  }
}

interface YouTubePlayer {
  getCurrentTime(): number
  seekTo(seconds: number, allowSeekAhead: boolean): void
  destroy(): void
}

const API_SRC = 'https://www.youtube.com/iframe_api'

/** Load the IFrame API once per page, and let every caller await the same load. */
function loadApi(): Promise<void> {
  if (window.YT?.Player) return Promise.resolve()
  return new Promise((resolve) => {
    const previous = window.onYouTubeIframeAPIReady
    window.onYouTubeIframeAPIReady = () => {
      previous?.()
      resolve()
    }
    if (!document.querySelector(`script[src="${API_SRC}"]`)) {
      const script = document.createElement('script')
      script.src = API_SRC
      document.head.appendChild(script)
    }
  })
}

/**
 * The video, and the clock that drives the brain.
 *
 * Playback position is polled rather than pushed, because the IFrame API has no
 * time event. Twenty times a second is smoother than the fly updates anyway.
 */
export default function VideoPreview({ video, onTime, seekTo }: Props) {
  const host = useRef<HTMLDivElement>(null)
  const player = useRef<YouTubePlayer | null>(null)
  const [ready, setReady] = useState(false)
  const [blocked, setBlocked] = useState(false)

  useEffect(() => {
    let cancelled = false
    let poll = 0

    loadApi().then(() => {
      if (cancelled || !host.current || !window.YT) return
      player.current = new window.YT.Player(host.current, {
        videoId: video.id,
        playerVars: { modestbranding: 1, rel: 0, playsinline: 1 },
        events: {
          onReady: () => {
            if (cancelled) return
            setReady(true)
            poll = window.setInterval(() => {
              const current = player.current?.getCurrentTime?.()
              if (typeof current === 'number') onTime(current)
            }, 50)
          },
          onError: () => setBlocked(true),
        },
      })
    })

    return () => {
      cancelled = true
      window.clearInterval(poll)
      player.current?.destroy?.()
      player.current = null
    }
  }, [video.id, onTime])

  useEffect(() => {
    if (seekTo != null && ready) player.current?.seekTo(seekTo, true)
  }, [seekTo, ready])

  return (
    <div className="video">
      <div className="video-frame">
        <div ref={host} />
      </div>
      <div className="video-meta">
        <a href={video.watchUrl} target="_blank" rel="noreferrer noopener" className="video-title">
          {video.title}
        </a>
        <span className="video-channel">{video.channel}</span>
        {blocked && (
          <span className="video-blocked">
            The uploader blocks embedding; use Replay to watch the fly instead.
          </span>
        )}
      </div>
    </div>
  )
}
