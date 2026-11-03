import type { Note } from '../api'

interface SidebarProps {
  notes: Note[]
  selectedId: number | null
  disabled: boolean
  creating: boolean
  onCreate: () => void
  onSelect: (note: Note) => void
}

function formatUpdated(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

export function Sidebar({ notes, selectedId, disabled, creating, onCreate, onSelect }: SidebarProps) {
  return (
    <aside className="sidebar">
      <button type="button" className="btn btn-primary" onClick={onCreate} disabled={disabled}>
        {creating ? 'Creating…' : 'New note'}
      </button>

      {notes.length === 0 ? (
        <p className="muted">No notes yet.</p>
      ) : (
        <ul className="note-list">
          {notes.map((note) => (
            <li key={note.id}>
              <button
                type="button"
                className={note.id === selectedId ? 'note-item note-item--active' : 'note-item'}
                aria-current={note.id === selectedId ? 'true' : undefined}
                onClick={() => onSelect(note)}
                disabled={disabled}
              >
                <span className="note-item__title">{note.title.trim() || 'Untitled'}</span>
                <span className="note-item__date">{formatUpdated(note.updated_at)}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </aside>
  )
}
