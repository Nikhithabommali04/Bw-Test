import { useEffect, useState } from 'react';
import { fetchTasks, createTask, updateTaskStatus, deleteTask } from './api.js';

const COLUMNS = [
  { status: 'todo', label: 'To Do' },
  { status: 'in_progress', label: 'In Progress' },
  { status: 'done', label: 'Done' },
];

const LOAD_ERROR = 'Could not load tasks. Please try again.';
const SAVE_ERROR = 'Something went wrong. Please try again.';

export default function App() {
  const [tasks, setTasks] = useState([]);
  const [title, setTitle] = useState('');
  const [formError, setFormError] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    fetchTasks()
      .then(setTasks)
      .catch(() => setError(LOAD_ERROR));
  }, []);

  async function handleAdd(e) {
    e.preventDefault();
    const trimmed = title.trim();
    if (!trimmed) {
      setFormError('Title cannot be empty.');
      return;
    }
    setFormError('');
    setError('');
    try {
      const task = await createTask(trimmed, 'todo');
      setTasks((prev) => [...prev, task]);
      setTitle('');
    } catch {
      setError(SAVE_ERROR);
    }
  }

  async function handleMove(task, status) {
    setError('');
    try {
      const updated = await updateTaskStatus(task.id, status);
      setTasks((prev) => prev.map((t) => (t.id === task.id ? updated : t)));
    } catch {
      setError(SAVE_ERROR);
    }
  }

  async function handleDelete(id) {
    setError('');
    try {
      await deleteTask(id);
      setTasks((prev) => prev.filter((t) => t.id !== id));
    } catch {
      setError(SAVE_ERROR);
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>TaskBoard</h1>
        <form className="add-form" onSubmit={handleAdd} noValidate>
          <input
            type="text"
            placeholder="New task title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            aria-label="New task title"
          />
          <button type="submit">Add task</button>
        </form>
        {formError && <p className="message message-error">{formError}</p>}
      </header>

      {error && (
        <p className="message message-error" role="alert">
          {error}
        </p>
      )}

      <main className="board">
        {COLUMNS.map((col) => {
          const columnTasks = tasks.filter((t) => t.status === col.status);
          return (
            <section className="column" key={col.status} aria-label={col.label}>
              <h2>
                {col.label} <span className="count">{columnTasks.length}</span>
              </h2>
              {columnTasks.length === 0 && <p className="empty">No tasks</p>}
              {columnTasks.map((task) => (
                <article className="card" key={task.id}>
                  <p className="card-title">{task.title}</p>
                  <div className="card-actions">
                    {COLUMNS.filter((c) => c.status !== col.status).map((target) => (
                      <button
                        key={target.status}
                        type="button"
                        className="btn-move"
                        onClick={() => handleMove(task, target.status)}
                      >
                        Move to {target.label}
                      </button>
                    ))}
                    <button
                      type="button"
                      className="btn-delete"
                      onClick={() => handleDelete(task.id)}
                    >
                      Delete
                    </button>
                  </div>
                </article>
              ))}
            </section>
          );
        })}
      </main>
    </div>
  );
}
