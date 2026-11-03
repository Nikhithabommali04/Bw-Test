export interface Note {
  id: number
  title: string
  body: string
  created_at: string
  updated_at: string
}

export interface NoteInput {
  title: string
  body: string
}

export interface Link {
  id: number
  url: string
  title: string
  tag: string
  created_at: string
}

export interface LinkInput {
  url: string
  title: string
  tag: string
}

const API_BASE: string = import.meta.env.VITE_API_URL ?? ''

export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

// FastAPI errors carry a `detail` field: a string for HTTPException, or a list
// of validation items that each have a `msg`.
async function readErrorDetail(res: Response): Promise<string> {
  const fallback = `Request failed (HTTP ${res.status})`

  let data: unknown
  try {
    data = await res.json()
  } catch {
    return fallback
  }

  if (!isRecord(data)) return fallback

  const { detail } = data
  if (typeof detail === 'string' && detail.length > 0) return detail

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item: unknown) => (isRecord(item) && typeof item.msg === 'string' ? item.msg : null))
      .filter((msg): msg is string => msg !== null)
    if (messages.length > 0) return messages.join('; ')
  }

  return fallback
}

async function send(
  path: string,
  method: 'GET' | 'POST' | 'PUT' | 'DELETE',
  body?: NoteInput | LinkInput,
): Promise<Response> {
  let res: Response
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new ApiError('Could not reach the server. Check your connection and try again.', 0)
  }

  if (!res.ok) {
    throw new ApiError(await readErrorDetail(res), res.status)
  }
  return res
}

export async function listNotes(): Promise<Note[]> {
  const res = await send('/api/notes', 'GET')
  return (await res.json()) as Note[]
}

export async function createNote(): Promise<Note> {
  const res = await send('/api/notes', 'POST', { title: '', body: '' })
  return (await res.json()) as Note
}

export async function updateNote(id: number, input: NoteInput): Promise<Note> {
  const res = await send(`/api/notes/${id}`, 'PUT', input)
  return (await res.json()) as Note
}

export async function deleteNote(id: number): Promise<void> {
  await send(`/api/notes/${id}`, 'DELETE')
}

export async function listLinks(tag?: string): Promise<Link[]> {
  const query = tag ? `?tag=${encodeURIComponent(tag)}` : ''
  const res = await send(`/api/links${query}`, 'GET')
  return (await res.json()) as Link[]
}

export async function createLink(input: LinkInput): Promise<Link> {
  const res = await send('/api/links', 'POST', input)
  return (await res.json()) as Link
}

export async function deleteLink(id: number): Promise<void> {
  await send(`/api/links/${id}`, 'DELETE')
}
