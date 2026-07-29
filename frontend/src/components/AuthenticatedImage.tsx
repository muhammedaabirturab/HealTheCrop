import { useEffect, useState } from 'react'
import { ImageOff } from 'lucide-react'
import { api } from '../lib/api'

// The admin image endpoints require a Bearer token, which a plain <img src>
// can't attach — this fetches the bytes via the shared authenticated axios
// instance and renders them through a local object URL instead.
export default function AuthenticatedImage({ src, alt, className }: { src: string; alt: string; className?: string }) {
  const [objectUrl, setObjectUrl] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let currentUrl: string | null = null
    let cancelled = false
    setFailed(false)
    setObjectUrl(null)

    api.get(src, { responseType: 'blob' })
      .then((res) => {
        if (cancelled) return
        currentUrl = URL.createObjectURL(res.data)
        setObjectUrl(currentUrl)
      })
      .catch(() => !cancelled && setFailed(true))

    return () => {
      cancelled = true
      if (currentUrl) URL.revokeObjectURL(currentUrl)
    }
  }, [src])

  if (failed) {
    return (
      <div className={`flex items-center justify-center bg-forest/10 text-forest/50 ${className}`}>
        <ImageOff size={20} />
      </div>
    )
  }
  if (!objectUrl) {
    return <div className={`animate-pulse bg-forest/10 ${className}`} />
  }
  return <img src={objectUrl} alt={alt} className={className} />
}
