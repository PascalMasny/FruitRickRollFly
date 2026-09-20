import { useState } from 'react'

interface Props {
  onSubmit(url: string): void
  busy: boolean
  disabled: boolean
}

const EXAMPLES = [
  { label: 'the classic', url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ' },
  { label: 'a hard negative', url: 'https://www.youtube.com/watch?v=BeyEGebJ1l4' },
  { label: 'a piano cover', url: 'https://www.youtube.com/watch?v=rTga41r3a4s' },
]

export default function UrlInput({ onSubmit, busy, disabled }: Props) {
  const [value, setValue] = useState('')

  return (
    <form
      className="url-form"
      onSubmit={(event) => {
        event.preventDefault()
        if (value.trim()) onSubmit(value.trim())
      }}
    >
      <div className="url-row">
        <span className="url-prompt">http://</span>
        <input
          className="url-input"
          type="url"
          inputMode="url"
          spellCheck={false}
          placeholder="https://www.youtube.com/watch?v=..."
          value={value}
          onChange={(event) => setValue(event.target.value)}
          aria-label="YouTube link"
          disabled={disabled}
        />
        <button className="url-submit" type="submit" disabled={busy || disabled || !value.trim()}>
          {busy ? 'listening' : 'play it 2 me'}
        </button>
      </div>
      <div className="url-examples">
        <span className="url-examples-label">or try:</span>
        {EXAMPLES.map((example) => (
          <button
            key={example.url}
            type="button"
            className="chip"
            onClick={() => {
              setValue(example.url)
              onSubmit(example.url)
            }}
            disabled={busy || disabled}
          >
            {example.label}
          </button>
        ))}
      </div>
    </form>
  )
}
