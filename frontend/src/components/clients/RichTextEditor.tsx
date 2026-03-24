'use client'

import { useRef } from 'react'
import { cn } from '@/lib/utils'

interface Props {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  rows?: number
  disabled?: boolean
}

interface ToolbarAction {
  label: string
  title: string
  action: (textarea: HTMLTextAreaElement, value: string, onChange: (v: string) => void) => void
}

function wrapSelection(
  textarea: HTMLTextAreaElement,
  value: string,
  onChange: (v: string) => void,
  prefix: string,
  suffix: string
) {
  const start = textarea.selectionStart
  const end = textarea.selectionEnd
  const selected = value.slice(start, end)
  const newValue = value.slice(0, start) + prefix + selected + suffix + value.slice(end)
  onChange(newValue)
  // Restore cursor inside the markers after React re-render
  requestAnimationFrame(() => {
    textarea.setSelectionRange(start + prefix.length, end + prefix.length)
    textarea.focus()
  })
}

function prefixLine(
  textarea: HTMLTextAreaElement,
  value: string,
  onChange: (v: string) => void,
  linePrefix: string
) {
  const start = textarea.selectionStart
  // Find the start of the current line
  const lineStart = value.lastIndexOf('\n', start - 1) + 1
  const newValue = value.slice(0, lineStart) + linePrefix + value.slice(lineStart)
  onChange(newValue)
  requestAnimationFrame(() => {
    const newCursor = start + linePrefix.length
    textarea.setSelectionRange(newCursor, newCursor)
    textarea.focus()
  })
}

const TOOLBAR_ACTIONS: ToolbarAction[] = [
  {
    label: 'B',
    title: 'Bold — wraps selection with **',
    action: (ta, val, onChange) => wrapSelection(ta, val, onChange, '**', '**'),
  },
  {
    label: 'I',
    title: 'Italic — wraps selection with *',
    action: (ta, val, onChange) => wrapSelection(ta, val, onChange, '*', '*'),
  },
  {
    label: 'H',
    title: 'Heading — prefixes line with ##',
    action: (ta, val, onChange) => prefixLine(ta, val, onChange, '## '),
  },
  {
    label: '•',
    title: 'Bullet list — prefixes line with -',
    action: (ta, val, onChange) => prefixLine(ta, val, onChange, '- '),
  },
  {
    label: '1.',
    title: 'Numbered list — prefixes line with 1.',
    action: (ta, val, onChange) => prefixLine(ta, val, onChange, '1. '),
  },
]

export default function RichTextEditor({
  value,
  onChange,
  placeholder = 'Write your notes here…',
  rows = 8,
  disabled = false,
}: Props) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  function handleAction(action: ToolbarAction['action']) {
    if (!textareaRef.current || disabled) return
    action(textareaRef.current, value, onChange)
  }

  return (
    <div
      className={cn(
        'flex flex-col rounded-md border border-slate-300 bg-white shadow-sm',
        'focus-within:border-indigo-500 focus-within:ring-2 focus-within:ring-indigo-500/30',
        'transition-colors duration-150',
        disabled && 'opacity-60'
      )}
    >
      {/* Toolbar */}
      <div className="flex items-center gap-0.5 border-b border-slate-200 px-2 py-1.5">
        {TOOLBAR_ACTIONS.map((item) => (
          <button
            key={item.label}
            type="button"
            title={item.title}
            disabled={disabled}
            onClick={() => handleAction(item.action)}
            className={cn(
              'min-w-[2rem] rounded px-2 py-1 text-xs font-semibold text-slate-600',
              'hover:bg-indigo-50 hover:text-indigo-700',
              'focus:outline-none focus:ring-2 focus:ring-indigo-500/40',
              'transition-colors duration-100',
              item.label === 'B' && 'font-extrabold',
              item.label === 'I' && 'italic',
              disabled && 'cursor-not-allowed'
            )}
          >
            {item.label}
          </button>
        ))}

        <span className="ml-auto text-xs text-slate-400 select-none">Markdown</span>
      </div>

      {/* Textarea */}
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        rows={rows}
        disabled={disabled}
        className={cn(
          'w-full resize-y rounded-b-md bg-transparent px-3 py-2.5',
          'font-mono text-sm leading-relaxed text-slate-800 placeholder:text-slate-400',
          'focus:outline-none',
          disabled && 'cursor-not-allowed'
        )}
      />

      {/* Hint */}
      <div className="border-t border-slate-100 px-3 py-1.5">
        <p className="text-[11px] text-slate-400">
          Use{' '}
          <code className="rounded bg-slate-100 px-1 font-mono text-[10px] text-slate-500">
            **bold**
          </code>
          ,{' '}
          <code className="rounded bg-slate-100 px-1 font-mono text-[10px] text-slate-500">
            *italic*
          </code>
          ,{' '}
          <code className="rounded bg-slate-100 px-1 font-mono text-[10px] text-slate-500">
            ## Heading
          </code>
          ,{' '}
          <code className="rounded bg-slate-100 px-1 font-mono text-[10px] text-slate-500">
            - bullet
          </code>
          ,{' '}
          <code className="rounded bg-slate-100 px-1 font-mono text-[10px] text-slate-500">
            1. numbered
          </code>
        </p>
      </div>
    </div>
  )
}
