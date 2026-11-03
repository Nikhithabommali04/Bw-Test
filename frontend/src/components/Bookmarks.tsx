import { useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react'
import { ApiError, createLink, deleteLink, listLinks, type Link } from '../api'

interface TagGroup {
  tag: string | null
  links: Link[]
}

function isHttpUrl(value: string): boolean {
  try {
    const url = new URL(value)
    return url.protocol === 'http:' || url.protocol === 'https:'
  } catch {
    return false
  }
}

function errorText(err: unknown): string {
  return err instanceof ApiError ? err.message : 'Something went wrong. Please try again.'
}

// Copies text via the async Clipboard API when available (secure contexts only),
// otherwise falls back to a hidden textarea and execCommand for plain HTTP.
async function copyToClipboard(text: string): Promise<boolean> {
  if (window.isSecureContext && navigator.clipboard) {
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch {
      return false
    }
  }

  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.setAttribute('readonly', '')
  textarea.style.position = 'fixed'
  textarea.style.opacity = '0'
  document.body.appendChild(textarea)
  try {
    textarea.select()
    return document.execCommand('copy')
  } catch {
    return false
  } finally {
    textarea.remove()
  }
}

function sortNewestFirst(links: Link[]): Link[] {
  return [...links].sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at))
}

// Groups newest-first links by tag. Untagged links go last.
function groupByTag(links: Link[]): TagGroup[] {
  const groups = new Map<string | null, Link[]>()
  for (const link of links) {
    const tag = link.tag.trim() || null
    const group = groups.get(tag)
    if (group) group.push(link)
    else groups.set(tag, [link])
  }

  return [...groups.entries()]
    .map(([tag, groupLinks]) => ({ tag, links: groupLinks }))
    .sort((a, b) => {
      if (a.tag === b.tag) return 0
      if (a.tag === null) return 1
      if (b.tag === null) return -1
      return a.tag.localeCompare(b.tag)
    })
}

export function Bookmarks() {
  const [links, setLinks] = useState<Link[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')

  const [url, setUrl] = useState('')
  const [title, setTitle] = useState('')
  const [tag, setTag] = useState('')
  const [formError, setFormError] = useState('')
  const [adding, setAdding] = useState(false)

  const [deletingId, setDeletingId] = useState<number | null>(null)
  const [actionError, setActionError] = useState('')

  const [copyFeedback, setCopyFeedback] = useState<{ id: number; message: string } | null>(null)
  const copyTimerRef = useRef<number | null>(null)
  const mountedRef = useRef(false)

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
      if (copyTimerRef.current !== null) window.clearTimeout(copyTimerRef.current)
    }
  }, [])

  useEffect(() => {
    let ignore = false
    listLinks().then(
      (data) => {
        if (ignore) return
        setLinks(sortNewestFirst(data))
        setLoading(false)
      },
      (err: unknown) => {
        if (ignore) return
        setLoadError(errorText(err))
        setLoading(false)
      },
    )
    return () => {
      ignore = true
    }
  }, [])

  const handleAdd = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (adding) return

    const trimmedUrl = url.trim()
    if (!isHttpUrl(trimmedUrl)) {
      setFormError('Enter a valid URL starting with http:// or https://.')
      return
    }

    setAdding(true)
    setFormError('')
    try {
      const link = await createLink({ url: trimmedUrl, title: title.trim(), tag: tag.trim() })
      setLinks((prev) => sortNewestFirst([link, ...prev]))
      setUrl('')
      setTitle('')
      setTag('')
    } catch (err) {
      setFormError(errorText(err))
    } finally {
      setAdding(false)
    }
  }

  const handleDelete = async (id: number) => {
    setDeletingId(id)
    setActionError('')
    try {
      await deleteLink(id)
      setLinks((prev) => prev.filter((link) => link.id !== id))
    } catch (err) {
      setActionError(errorText(err))
    } finally {
      setDeletingId(null)
    }
  }

  const handleCopy = async (link: Link) => {
    const copied = await copyToClipboard(link.url)
    if (!mountedRef.current) return
    if (copyTimerRef.current !== null) window.clearTimeout(copyTimerRef.current)
    setCopyFeedback({ id: link.id, message: copied ? 'Copied' : 'Copy failed' })
    copyTimerRef.current = window.setTimeout(() => {
      setCopyFeedback(null)
      copyTimerRef.current = null
    }, 2000)
  }

  let list: ReactNode
  if (loading) {
    list = <p className="muted">Loading bookmarks…</p>
  } else if (loadError) {
    list = (
      <p className="status status--error" role="alert">
        {loadError}
      </p>
    )
  } else if (links.length === 0) {
    list = <p className="muted">No bookmarks yet. Add one above.</p>
  } else {
    list = groupByTag(links).map((group) => (
      <section key={group.tag ?? ''} className="bookmark-group" aria-label={group.tag ?? 'Untagged'}>
        <h2 className="bookmark-group__title">{group.tag ?? 'Untagged'}</h2>
        <ul className="bookmark-list">
          {group.links.map((link) => {
            const label = link.title.trim() || link.url
            return (
              <li key={link.id} className="bookmark-item">
                <div className="bookmark-item__text">
                  <span className="bookmark-item__title">{label}</span>
                  {isHttpUrl(link.url) ? (
                    <a className="bookmark-item__url" href={link.url} target="_blank" rel="noopener">
                      {link.url}
                    </a>
                  ) : (
                    <span className="bookmark-item__url">{link.url}</span>
                  )}
                </div>
                <button
                  type="button"
                  className="btn btn-danger-outline"
                  onClick={() => void handleDelete(link.id)}
                  disabled={deletingId !== null}
                  aria-label={`Delete ${label}`}
                >
                  {deletingId === link.id ? 'Deleting…' : 'Delete'}
                </button>
                <button
                  type="button"
                  className="btn"
                  onClick={() => void handleCopy(link)}
                  aria-label={`Copy link for ${label}`}
                >
                  Copy link
                </button>
                <span className="muted" role="status">
                  {copyFeedback?.id === link.id ? copyFeedback.message : ''}
                </span>
              </li>
            )
          })}
        </ul>
      </section>
    ))
  }

  return (
    <section className="bookmarks" aria-label="Bookmarks">
      <form className="bookmark-form" onSubmit={(event) => void handleAdd(event)} noValidate>
        <label className="field">
          <span className="field__label">URL</span>
          <input
            type="url"
            value={url}
            placeholder="https://example.com"
            onChange={(event) => setUrl(event.target.value)}
            disabled={adding}
          />
        </label>

        <label className="field">
          <span className="field__label">Title</span>
          <input
            type="text"
            value={title}
            placeholder="Optional"
            onChange={(event) => setTitle(event.target.value)}
            disabled={adding}
          />
        </label>

        <label className="field">
          <span className="field__label">Tag</span>
          <input
            type="text"
            value={tag}
            placeholder="Optional"
            onChange={(event) => setTag(event.target.value)}
            disabled={adding}
          />
        </label>

        <div className="editor__actions">
          <button type="submit" className="btn btn-primary" disabled={adding}>
            {adding ? 'Adding…' : 'Add link'}
          </button>
        </div>

        <p
          className={formError ? 'status status--error' : 'status'}
          role={formError ? 'alert' : 'status'}
        >
          {formError}
        </p>
      </form>

      {actionError && (
        <p className="status status--error" role="alert">
          {actionError}
        </p>
      )}

      <div className="bookmark-groups">{list}</div>
    </section>
  )
}
