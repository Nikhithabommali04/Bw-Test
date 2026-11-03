import { useCallback, useEffect, useState, type ReactNode } from 'react'
import { ApiError, createNote, deleteNote, listNotes, updateNote, type Note } from './api'
import { NoteEditor, type SaveState } from './components/NoteEditor'
import { Sidebar } from './components/Sidebar'

type LoadState = 'loading' | 'ready' | 'error'

function sortNewestFirst(notes: Note[]): Note[] {
  return [...notes].sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at))
}

function errorText(err: unknown): string {
  return err instanceof ApiError ? err.message : 'Something went wrong. Please try again.'
}

export default function App() {
  const [notes, setNotes] = useState<Note[]>([])
  const [loadState, setLoadState] = useState<LoadState>('loading')
  const [loadError, setLoadError] = useState('')

  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')

  const [saveState, setSaveState] = useState<SaveState>('idle')
  const [saveError, setSaveError] = useState('')
  const [actionError, setActionError] = useState('')
  const [creating, setCreating] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [confirmingDelete, setConfirmingDelete] = useState(false)

  const selected = notes.find((note) => note.id === selectedId) ?? null
  const dirty = selected !== null && (title !== selected.title || body !== selected.body)
  const saving = saveState === 'saving'
  const listLocked = loadState !== 'ready' || creating || deleting || saving

  // Replaces the editor contents. Passing null shows the empty state.
  const showNote = useCallback((note: Note | null) => {
    setSelectedId(note?.id ?? null)
    setTitle(note?.title ?? '')
    setBody(note?.body ?? '')
    setSaveState('idle')
    setSaveError('')
    setActionError('')
    setConfirmingDelete(false)
  }, [])

  const applyLoadedNotes = useCallback(
    (data: Note[]) => {
      const sorted = sortNewestFirst(data)
      setNotes(sorted)
      setLoadState('ready')
      showNote(sorted[0] ?? null)
    },
    [showNote],
  )

  const applyLoadError = useCallback((err: unknown) => {
    setLoadError(errorText(err))
    setLoadState('error')
  }, [])

  useEffect(() => {
    let ignore = false
    listNotes().then(
      (data) => {
        if (!ignore) applyLoadedNotes(data)
      },
      (err: unknown) => {
        if (!ignore) applyLoadError(err)
      },
    )
    return () => {
      ignore = true
    }
  }, [applyLoadedNotes, applyLoadError])

  const retryLoad = () => {
    setLoadState('loading')
    setLoadError('')
    listNotes().then(applyLoadedNotes, applyLoadError)
  }

  const handleCreate = async () => {
    setCreating(true)
    setActionError('')
    try {
      const note = await createNote()
      setNotes((prev) => sortNewestFirst([note, ...prev]))
      showNote(note)
    } catch (err) {
      setActionError(errorText(err))
    } finally {
      setCreating(false)
    }
  }

  const handleSave = async () => {
    if (!selected || !dirty) return
    setSaveState('saving')
    setSaveError('')
    try {
      const updated = await updateNote(selected.id, { title, body })
      setNotes((prev) => sortNewestFirst(prev.map((note) => (note.id === updated.id ? updated : note))))
      setSaveState('saved')
    } catch (err) {
      setSaveError(errorText(err))
      setSaveState('error')
    }
  }

  const handleConfirmDelete = async () => {
    if (!selected) return
    setDeleting(true)
    setActionError('')
    try {
      await deleteNote(selected.id)
      const index = notes.findIndex((note) => note.id === selected.id)
      const remaining = notes.filter((note) => note.id !== selected.id)
      setNotes(remaining)
      // Select the note that now sits where the deleted one was, if any.
      showNote(remaining.length === 0 ? null : remaining[Math.min(index, remaining.length - 1)])
    } catch (err) {
      setActionError(errorText(err))
      setConfirmingDelete(false)
    } finally {
      setDeleting(false)
    }
  }

  let main: ReactNode
  if (loadState === 'loading') {
    main = <p className="empty-state">Loading notes…</p>
  } else if (loadState === 'error') {
    main = (
      <div className="empty-state">
        <p className="status status--error" role="alert">{loadError}</p>
        <button type="button" className="btn" onClick={retryLoad}>
          Try again
        </button>
      </div>
    )
  } else if (selected) {
    main = (
      <NoteEditor
        title={title}
        body={body}
        dirty={dirty}
        saveState={saveState}
        saveError={saveError}
        deleting={deleting}
        confirmingDelete={confirmingDelete}
        onTitleChange={setTitle}
        onBodyChange={setBody}
        onSave={() => void handleSave()}
        onRequestDelete={() => setConfirmingDelete(true)}
        onCancelDelete={() => setConfirmingDelete(false)}
        onConfirmDelete={() => void handleConfirmDelete()}
      />
    )
  } else {
    main = (
      <p className="empty-state">
        {notes.length === 0 ? 'No notes yet. Create one with “New note”.' : 'Select a note to start editing.'}
      </p>
    )
  }

  return (
    <div className="app">
      <Sidebar
        notes={notes}
        selectedId={selectedId}
        disabled={listLocked}
        creating={creating}
        onCreate={() => void handleCreate()}
        onSelect={showNote}
      />
      <main className="main">
        {actionError && (
          <p className="status status--error" role="alert">
            {actionError}
          </p>
        )}
        {main}
      </main>
    </div>
  )
}
