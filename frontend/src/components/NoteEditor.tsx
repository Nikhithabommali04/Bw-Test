export type SaveState = 'idle' | 'saving' | 'saved' | 'error'

interface NoteEditorProps {
  title: string
  body: string
  dirty: boolean
  saveState: SaveState
  saveError: string
  deleting: boolean
  confirmingDelete: boolean
  onTitleChange: (value: string) => void
  onBodyChange: (value: string) => void
  onSave: () => void
  onRequestDelete: () => void
  onCancelDelete: () => void
  onConfirmDelete: () => void
}

function statusText(dirty: boolean, saveState: SaveState, saveError: string): string {
  if (saveState === 'saving') return 'Saving…'
  if (saveState === 'error') return saveError
  if (dirty) return 'Unsaved changes'
  if (saveState === 'saved') return 'Saved'
  return ''
}

export function NoteEditor({
  title,
  body,
  dirty,
  saveState,
  saveError,
  deleting,
  confirmingDelete,
  onTitleChange,
  onBodyChange,
  onSave,
  onRequestDelete,
  onCancelDelete,
  onConfirmDelete,
}: NoteEditorProps) {
  const status = statusText(dirty, saveState, saveError)
  const saving = saveState === 'saving'

  return (
    <form
      className="editor"
      onSubmit={(event) => {
        event.preventDefault()
        if (dirty && !saving) onSave()
      }}
    >
      <label className="field">
        <span className="field__label">Title</span>
        <input
          type="text"
          value={title}
          placeholder="Untitled"
          onChange={(event) => onTitleChange(event.target.value)}
          disabled={deleting}
        />
      </label>

      <label className="field">
        <span className="field__label">Body</span>
        <textarea
          className="body-input"
          value={body}
          onChange={(event) => onBodyChange(event.target.value)}
          disabled={deleting}
        />
      </label>

      <div className="editor__actions">
        <button type="submit" className="btn btn-primary" disabled={!dirty || saving || deleting}>
          Save
        </button>

        {confirmingDelete ? (
          <>
            <span className="muted">Delete this note?</span>
            <button type="button" className="btn btn-danger" onClick={onConfirmDelete} disabled={deleting}>
              {deleting ? 'Deleting…' : 'Yes, delete'}
            </button>
            <button type="button" className="btn" onClick={onCancelDelete} disabled={deleting}>
              Cancel
            </button>
          </>
        ) : (
          <button type="button" className="btn btn-danger-outline" onClick={onRequestDelete} disabled={deleting}>
            Delete
          </button>
        )}
      </div>

      <p
        className={saveState === 'error' ? 'status status--error' : 'status'}
        role={saveState === 'error' ? 'alert' : 'status'}
      >
        {status}
      </p>
    </form>
  )
}
