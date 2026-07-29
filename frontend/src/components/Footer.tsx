import { Leaf } from 'lucide-react'

export default function Footer() {
  return (
    <footer className="mt-auto flex items-center justify-center gap-3 py-8 bg-forest/5">
      <span className="h-px w-16 bg-forest/30" />
      <Leaf size={18} className="text-forest" />
      <span className="h-px w-16 bg-forest/30" />
    </footer>
  )
}
