import { api } from './api'

// A plain <a href> can't attach the Authorization header the CSV export
// endpoints require, so this fetches the file as a blob (with auth already
// applied by the shared axios instance) and triggers the browser's normal
// save-file flow from the resulting object URL.
export async function downloadAuthenticatedFile(url: string, filename: string): Promise<void> {
  const response = await api.get(url, { responseType: 'blob' })
  const objectUrl = URL.createObjectURL(response.data)
  const link = document.createElement('a')
  link.href = objectUrl
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(objectUrl)
}
