import {
  useEffect,
  useRef,
  useState,
  type Dispatch,
  type FormEvent,
  type SetStateAction,
} from 'react'
import { motion } from 'framer-motion'
import { CalendarPlusIcon, CheckCircle2Icon, PaperclipIcon, SendIcon } from 'lucide-react'
import {
  DraftAttachmentBubble,
  MessageBubble,
  type Message,
  type MessageAttachment,
} from './MessageBubble'
import {
  importTrainingPlan,
  scheduleSessions,
  streamChatCompletion,
  type ApiMessage,
} from '../api'
import { formatRestDaysForApi } from '../restDays'

interface ChatAreaProps {
  messages: Message[]
  setMessages: Dispatch<SetStateAction<Message[]>>
  restDays: string[]
  durationMin: number
}

type PendingAttachment = {
  id: string
  file: File
  previewUrl: string | null
}

const ACCEPTED_FILE_TYPES = /^image\/(jpeg|png|webp)$|^application\/pdf$/

function toApiMessages(msgs: Message[]): ApiMessage[] {
  return msgs.map((m) => ({ role: m.role, content: m.content }))
}

function buildCoachMessage(
  userText: string,
  extractedText: string,
  filename: string,
): string {
  const importBlock = `Programme importé depuis \`${filename}\` :\n\n${extractedText}`
  const tail = 'Propose un planning avec dates et horaires adaptés à mon agenda.'
  if (userText.trim()) {
    return `${userText.trim()}\n\n${importBlock}\n\n${tail}`
  }
  return `${importBlock}\n\n${tail}`
}

function buildDisplayContent(userText: string, filename: string): string {
  if (userText.trim()) return userText.trim()
  return `Fichier joint : ${filename}`
}

export function ChatArea({
  messages,
  setMessages,
  restDays,
  durationMin,
}: ChatAreaProps) {
  const [inputValue, setInputValue] = useState('')
  const [busy, setBusy] = useState(false)
  const [importing, setImporting] = useState(false)
  const [pendingAttachment, setPendingAttachment] = useState<PendingAttachment | null>(
    null,
  )
  const [statusLine, setStatusLine] = useState<string | null>(null)
  const [conflictingSessions, setConflictingSessions] = useState<
    Record<string, unknown>[]
  >([])
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const textInputRef = useRef<HTMLTextAreaElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, busy, pendingAttachment])

  const removePendingAttachment = () => {
    setPendingAttachment((current) => {
      if (current?.previewUrl) URL.revokeObjectURL(current.previewUrl)
      return null
    })
  }

  const lastMessage = messages[messages.length - 1]
  const planReady =
    !busy &&
    !importing &&
    lastMessage?.role === 'agent' &&
    lastMessage.content.trim().length > 0

  const showWelcome = messages.length === 0 && !pendingAttachment
  const inputDisabled = busy || importing
  const canSend = Boolean(inputValue.trim() || pendingAttachment) && !inputDisabled

  const streamCoachReply = async (
    prior: Message[],
    userMessage: Message,
    apiContent: string,
  ) => {
    const assistantId = crypto.randomUUID()
    setMessages([...prior, userMessage, { id: assistantId, role: 'agent', content: '' }])
    setBusy(true)

    const apiUserMessage: ApiMessage = { role: 'user', content: apiContent }
    let acc = ''
    try {
      await streamChatCompletion(
        [...toApiMessages(prior), apiUserMessage],
        formatRestDaysForApi(restDays),
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

  const handleSend = async (e?: FormEvent) => {
    e?.preventDefault()
    if (!canSend) return

    setStatusLine(null)
    setConflictingSessions([])

    const userText = inputValue.trim()
    const attachment = pendingAttachment

    if (attachment) {
      const { file, previewUrl } = attachment
      const filename = file.name
      const messageAttachment: MessageAttachment = {
        filename,
        previewUrl: previewUrl ?? undefined,
        mimeType: file.type,
      }
      const displayContent = buildDisplayContent(userText, filename)

      setPendingAttachment(null)
      setInputValue('')

      const userMessage: Message = {
        id: crypto.randomUUID(),
        role: 'user',
        content: displayContent,
        attachment: messageAttachment,
      }

      setImporting(true)
      setStatusLine('Analyse du fichier…')

      try {
        const result = await importTrainingPlan(file)
        setStatusLine(null)
        const coachText = buildCoachMessage(
          userText,
          result.extracted_text,
          filename,
        )
        await streamCoachReply(messages, userMessage, coachText)
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Échec de l\'import'
        setStatusLine(msg && msg !== '{}' ? msg : 'Échec de l\'import du fichier.')
        setMessages((prev) => [...prev, userMessage])
      } finally {
        setImporting(false)
      }
      return
    }

    const text = userText
    setInputValue('')
    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: text,
    }
    await streamCoachReply(messages, userMessage, text)
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file || inputDisabled) return

    const mime = file.type.toLowerCase()
    if (!ACCEPTED_FILE_TYPES.test(mime)) {
      setStatusLine('Format non supporté. Utilise une image (JPEG, PNG, WebP) ou un PDF.')
      return
    }

    setStatusLine(null)
    setConflictingSessions([])

    if (pendingAttachment?.previewUrl) {
      URL.revokeObjectURL(pendingAttachment.previewUrl)
    }

    const previewUrl = mime.startsWith('image/') ? URL.createObjectURL(file) : null
    setPendingAttachment({ id: crypto.randomUUID(), file, previewUrl })
    textInputRef.current?.focus()
  }

  const handleSchedule = async () => {
    if (!messages.length || busy || importing) return
    setStatusLine(null)
    setConflictingSessions([])
    setBusy(true)
    try {
      const result = await scheduleSessions(
        toApiMessages(messages),
        formatRestDaysForApi(restDays),
        durationMin,
      )
      setConflictingSessions(result.conflicting_sessions ?? [])
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

  return (
    <div className="flex h-full min-h-0 flex-1 flex-col bg-white">
      <div className="flex shrink-0 items-center justify-center border-b border-slate-200 bg-[#F1F5F9] p-4 md:hidden">
        <span className="font-bold tracking-tight text-slate-900">Sports Planner Perso</span>
      </div>

      <div className="scrollbar-hide min-h-0 flex-1 overflow-y-auto p-4 md:p-8">
        <div className="mx-auto w-full max-w-4xl xl:max-w-5xl">
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

              {!busy && !importing && planReady ? (
                <div className="mb-4 flex justify-center">
                  <button
                    type="button"
                    onClick={handleSchedule}
                    className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-[#1E3A5F] shadow-sm transition-colors hover:bg-slate-50"
                  >
                    <CheckCircle2Icon size={16} />
                    Valider et planifier dans l&apos;agenda
                  </button>
                </div>
              ) : null}
            </div>
          )}

          {pendingAttachment ? (
            <div className={showWelcome ? 'mt-8' : ''}>
              <DraftAttachmentBubble
                filename={pendingAttachment.file.name}
                previewUrl={pendingAttachment.previewUrl}
                mimeType={pendingAttachment.file.type}
                onRemove={removePendingAttachment}
              />
            </div>
          ) : null}

          <div ref={messagesEndRef} />
        </div>
      </div>

      <div className="shrink-0 border-t border-slate-100 bg-white px-4 pb-6 pt-4 md:px-8">
        <div className="mx-auto max-w-4xl space-y-3 xl:max-w-5xl">
          {statusLine ? (
            <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-2 text-center text-xs text-slate-600">
              {statusLine}
            </div>
          ) : null}

          {conflictingSessions.length > 0 ? (
            <details className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-2 text-xs text-amber-900">
              <summary className="cursor-pointer font-medium">
                {conflictingSessions.length} séance(s) en conflit (non ajoutées)
              </summary>
              <ul className="mt-2 list-inside list-disc space-y-1 text-left">
                {conflictingSessions.map((s, i) => (
                  <li key={i}>
                    {String(s.title ?? 'Session')} — {String(s.date ?? '')}{' '}
                    {String(s.time ?? '')} ({String(s.duration_min ?? '')} min)
                  </li>
                ))}
              </ul>
            </details>
          ) : null}

          <form onSubmit={handleSend} className="group relative">
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp,application/pdf,.pdf"
              className="hidden"
              onChange={handleFileSelect}
              disabled={inputDisabled}
            />
            <textarea
              ref={textInputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  void handleSend()
                }
              }}
              rows={Math.min(8, Math.max(1, inputValue.split('\n').length))}
              placeholder={
                pendingAttachment
                  ? 'Ajoute du contexte (optionnel)…'
                  : 'Décris ton objectif sportif...'
              }
              disabled={inputDisabled}
              className="scrollbar-hide w-full resize-none rounded-2xl border border-slate-200 bg-white py-4 pl-14 pr-16 text-[15px] leading-relaxed text-slate-900 shadow-lg placeholder:text-slate-400 transition-all focus:border-blue-400 focus:outline-none focus:ring-1 focus:ring-blue-400 disabled:opacity-60"
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={inputDisabled}
              title="Importer une image ou un PDF"
              className="absolute bottom-2 left-2 top-2 flex aspect-square items-center justify-center rounded-xl text-slate-400 transition-colors hover:bg-slate-100 hover:text-[#1E3A5F] disabled:opacity-40"
            >
              <PaperclipIcon size={18} />
            </button>
            <button
              type="submit"
              disabled={!canSend}
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
