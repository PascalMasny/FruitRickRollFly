import { useEffect, useRef } from 'react'
import type { Video } from '../lib/types'

interface Props {
  video: Video
  src: string | null
  failed: boolean
  onElement(element: HTMLVideoElement | null): void
  onPlaying(playing: boolean): void
  onTime(seconds: number): void
  seekTo: number | null
}

/**
 * The video, played from our own copy, and the clock that drives the brain.
 *
 * This used to be a YouTube embed, which failed in the one case the whole
 * application is about: the uploads worth asking about are very often the ones
 * whose uploader has disabled embedding, and those rendered as a grey box
 * reading *this video is not available*. The file the fly listened to is
 * already on disk, so it is served from there and played in a plain <video>.
 *
 * Position is read on an animation frame rather than from `timeupdate`, which
 * fires about four times a second -- too coarse for a brain drawn at eight.
 */
export default function VideoPreview({
  video,
  src,
  failed,
  onElement,
  onPlaying,
  onTime,
  seekTo,
}: Props) {
  const element = useRef<HTMLVideoElement | null>(null)

  useEffect(() => {
    const player = element.current
    // `src` is in the dependencies because it has to be: until the download
    // lands there is no <video> for the ref to point at, and an effect that
    // only watched `onTime` would give up on that first empty pass and never
    // start the clock at all.
    if (!player || !src) return
    let raf = 0
    let last = 0
    const tick = (now: number) => {
      raf = requestAnimationFrame(tick)
      // Percepts arrive at about 8 Hz, so sampling at 25 is already finer
      // than anything downstream can show. Every frame would just be three
      // times the renders for the same picture.
      if (now - last < 40) return
      last = now
      if (!player.paused && !player.seeking) onTime(player.currentTime)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [onTime, src])

  useEffect(() => {
    const player = element.current
    if (!player || seekTo == null) return
    player.currentTime = seekTo
    onTime(seekTo)
  }, [seekTo, onTime])

  return (
    <div className="video-stack">
      <div className="video-frame">
        {src ? (
          <video
            ref={(node) => {
              element.current = node
              onElement(node)
            }}
            src={src}
            controls
            playsInline
            preload="metadata"
            onSeeked={(event) => onTime(event.currentTarget.currentTime)}
            onPlay={() => onPlaying(true)}
            onPause={() => onPlaying(false)}
            onEnded={() => onPlaying(false)}
          />
        ) : (
          <div className="video-pending">
            {failed ? "the video would not download" : "downloading the video"}
          </div>
        )}
      </div>
      <div className="video-meta">
        <a href={video.watchUrl} target="_blank" rel="noreferrer noopener" className="video-title">
          {video.title}
        </a>
        <span className="video-channel">{video.channel}</span>
      </div>
    </div>
  )
}
