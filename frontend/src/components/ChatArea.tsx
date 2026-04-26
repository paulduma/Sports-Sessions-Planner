import {
  useEffect,
  useRef,
  useState,
  type Dispatch,
  type FormEvent,
  type SetStateAction,
} from 'react'
import { motion } from 'framer-motion'
import { CalendarPlusIcon, CheckCircle2Icon, SendIcon } from 'lucide-react'
import { MessageBubble, type Message } from './MessageBubble'
import { scheduleSessions, streamChatCompletion, type ApiMessage } from '../api'

interface ChatAreaProps {
  messages: Message[]
  setMessages: Dispatch<SetStateAction<Message[]>>
  restDay: string
  durationMin: number
}

function toApiMessages(msgs: Message[]): ApiMessage[] {
  return msgs.map((m) => ({ role: m.role, content: m.content }))
}

export function ChatArea({
  messages,
  setMessages,
  restDay,
  durationMin,
}: ChatAreaProps) {
  const [inputValue, setInputValue] = useState('')
  const [busy, setBusy] = useState(false)
  const [statusLine, setStatusLine] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async (e: FormEvent) => {
    e.preventDefault()
    if (!inputValue.trim() || busy) return

    const text = inputValue.trim()
    setInputValue('')
    setStatusLine(null)

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: text,
    }

    const assistantId = crypto.randomUUID()
    const nextThread: Message[] = [
      ...messages,
      userMessage,
      { id: assistantId, role: 'agent', content: '' },
    ]
    setMessages(nextThread)
    setBusy(true)

    let acc = ''
    try {
      await streamChatCompletion(
        toApiMessages([...messages, userMessage]),
        restDay,
        durationMin,
        (delta) => {
          acc += delta
          setMessages((prev) =>
            prev.map((m) => (m.id === assistantId ? { ...m, content: acc } : m)),
          )
        },
      )
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Erreur réseau'
      setStatusLine(msg)
      setMessages((prev) => prev.filter((m) => m.id !== assistantId))
    } finally {
      setBusy(false)
    }
  }

  const handleSchedule = async () => {
    if (!messages.length || busy) return
    setStatusLine(null)
    setBusy(true)
    try {
      const result = await scheduleSessions(
        toApiMessages(messages),
        restDay,
        durationMin,
      )
      if (result.ok) {
        const w = result.warnings.filter(Boolean).join(' — ')
        setStatusLine(
          w
            ? `Ajouté ${result.scheduled_count} séance(s). ${w}`
            : `Ajouté ${result.scheduled_count} séance(s) à Google Calendar.`,
        )
      } else {
        const parts = [...result.errors, ...result.warnings].filter(Boolean)
        setStatusLine(parts.join(' — ') || 'Impossible de planifier.')
      }
    } catch (err) {
      setStatusLine(err instanceof Error ? err.message : 'Échec de la planification')
    } finally {
      setBusy(false)
    }
  }

  const lastAgentHasText = [...messages]
    .reverse()
    .find((m) => m.role === 'agent' && m.content.trim())

  const showWelcome = messages.length === 0

  return (
    <div className="relative flex h-full flex-1 flex-col bg-white">
      <div className="flex items-center justify-center border-b border-slate-200 bg-[#F1F5F9] p-4 md:hidden">
        <span className="font-bold tracking-tight text-slate-900">Sports Planner Perso</span>
      </div>

      <div className="scrollbar-hide flex-1 overflow-y-auto p-4 pb-32 md:p-8">
        <div className="mx-auto flex h-full w-full max-w-3xl flex-col">
          {showWelcome ? (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.4, ease: 'easeOut' }}
              className="mt-10 flex flex-1 flex-col items-center justify-center text-center md:mt-0"
            >
              <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl border border-blue-100 bg-blue-50">
                <CalendarPlusIcon size={32} className="text-[#1E3A5F]" />
              </div>
              <h1 className="mb-4 text-4xl font-bold tracking-tight text-slate-900 md:text-5xl">
                Programe{' '}
                <span className="text-[#1E3A5F]">d'entraînement</span>
              </h1>
              <p className="mb-10 max-w-lg text-lg text-slate-500">
                Préparation des prochains sessions et synchronisation avec Google Agenda.
              </p>

              <div className="flex max-w-2xl flex-wrap justify-center gap-3">
                <SuggestionBadge
                  text="🏃‍♂️ Plan semi-marathon"
                  onClick={() =>
                    setInputValue(
                      'Je veux préparer un semi-marathon en 12 semaines. Je peux courir 3x par semaine.',
                    )
                  }
                />
                <SuggestionBadge
                  text="🏋️‍♀️ Reprise musculation"
                  onClick={() =>
                    setInputValue(
                      'Je veux reprendre la musculation 3x par semaine. Fais-moi un programme Full Body.',
                    )
                  }
                />
                <SuggestionBadge
                  text="🧘‍♀️ Routine yoga matinale"
                  onClick={() =>
                    setInputValue(
                      'Crée-moi une routine de yoga de 15min pour tous les matins à 7h.',
                    )
                  }
                />
              </div>
            </motion.div>
          ) : (
            <div className="pt-4 md:pt-8">
              {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}
              <div ref={messagesEndRef} className="h-4" />
            </div>
          )}
        </div>
      </div>

      <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-white via-white to-transparent px-4 pb-6 pt-12 md:px-8">
        <div className="mx-auto max-w-3xl space-y-3">
          {statusLine ? (
            <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-2 text-center text-xs text-slate-600">
              {statusLine}
            </div>
          ) : null}

          {!showWelcome && lastAgentHasText ? (
            <div className="flex justify-center">
              <button
                type="button"
                disabled={busy}
                onClick={handleSchedule}
                className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-[#1E3A5F] shadow-sm transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <CheckCircle2Icon size={16} />
                Valider et planifier dans l&apos;agenda
              </button>
            </div>
          ) : null}

          <form onSubmit={handleSend} className="group relative">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Décris ton objectif sportif..."
              disabled={busy}
              className="w-full rounded-2xl border border-slate-200 bg-white py-4 pl-6 pr-16 text-[15px] text-slate-900 shadow-lg placeholder:text-slate-400 transition-all focus:border-blue-400 focus:outline-none focus:ring-1 focus:ring-blue-400 disabled:opacity-60"
            />
            <button
              type="submit"
              disabled={!inputValue.trim() || busy}
              className="absolute bottom-2 right-2 top-2 flex aspect-square items-center justify-center rounded-xl bg-[#1E3A5F] text-white transition-colors hover:bg-[#2a4f7a] disabled:opacity-40"
            >
              <SendIcon size={18} className="ml-0.5" />
            </button>
          </form>
          <div className="text-center">
            <span className="text-[11px] text-slate-400">
              Version beta - WIP
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}

function SuggestionBadge({
  text,
  onClick,
}: {
  text: string
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded-full border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm font-medium text-slate-600 transition-all hover:border-slate-300 hover:bg-slate-100 hover:text-slate-800 active:scale-95"
    >
      {text}
    </button>
  )
}
