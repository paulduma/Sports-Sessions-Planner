import { motion } from 'framer-motion'
import { BotIcon, FileTextIcon, UserIcon, XIcon } from 'lucide-react'
import ReactMarkdown from 'react-markdown'

export type MessageAttachment = {
  filename: string
  previewUrl?: string
  mimeType: string
}

export type Message = {
  id: string
  role: 'user' | 'agent'
  content: string
  attachment?: MessageAttachment
}

export function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user'
  return (
    <motion.div
      initial={{
        opacity: 0,
        y: 10,
      }}
      animate={{
        opacity: 1,
        y: 0,
      }}
      className={`mb-6 flex w-full ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      <div
        className={`flex w-full items-end gap-3 ${isUser ? 'max-w-[88%] flex-row-reverse self-end sm:max-w-[75%] md:max-w-[65%]' : 'max-w-full flex-row'}`}
      >
        <div
          className={`flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full ${isUser ? 'bg-[#1E3A5F] text-white' : 'border border-slate-200 bg-[#F1F5F9] text-slate-600'}`}
        >
          {isUser ? <UserIcon size={16} /> : <BotIcon size={16} />}
        </div>
        <div
          className={`rounded-2xl px-5 py-3.5 text-[15px] leading-relaxed ${isUser ? 'rounded-br-sm bg-[#1E3A5F] font-medium text-white shadow-sm' : 'rounded-bl-sm border border-slate-200/80 bg-[#F1F5F9] text-slate-700'}`}
        >
          {isUser ? (
            <div className="space-y-2">
              {message.attachment ? (
                <AttachmentPreview attachment={message.attachment} variant="user" />
              ) : null}
              {message.content ? (
                <span className="whitespace-pre-wrap">{message.content}</span>
              ) : null}
            </div>
          ) : (
            <div className="prose prose-sm prose-slate max-w-none prose-p:my-1.5 prose-ul:my-2 prose-li:my-0.5 prose-headings:mb-2 prose-headings:mt-3 first:prose-headings:mt-0 [&_li_ul]:mt-1.5 [&_li_ul_li]:my-0.5 [&_ul:not(li_ul):not(:first-child)]:mt-5 [&_ul:not(li_ul)>li]:mb-5 [&_ul:not(li_ul)>li]:pb-5 [&_ul:not(li_ul)>li:not(:last-child)]:border-b [&_ul:not(li_ul)>li:not(:last-child)]:border-slate-200/50">
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  )
}

function AttachmentPreview({
  attachment,
  variant = 'user',
}: {
  attachment: MessageAttachment
  variant?: 'user' | 'draft'
}) {
  if (attachment.previewUrl) {
    return (
      <img
        src={attachment.previewUrl}
        alt={attachment.filename}
        className={`max-h-56 w-full rounded-lg object-contain ${
          variant === 'user'
            ? 'border border-white/20'
            : 'border border-slate-200 bg-white'
        }`}
      />
    )
  }

  return (
    <div
      className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm ${
        variant === 'user'
          ? 'border border-white/20 bg-white/10'
          : 'border border-slate-200 bg-white text-slate-700'
      }`}
    >
      <FileTextIcon size={16} className="shrink-0 opacity-80" />
      <span className="truncate">{attachment.filename}</span>
    </div>
  )
}

export function DraftAttachmentBubble({
  filename,
  previewUrl,
  mimeType,
  onRemove,
}: {
  filename: string
  previewUrl: string | null
  mimeType: string
  onRemove: () => void
}) {
  const attachment: MessageAttachment = {
    filename,
    previewUrl: previewUrl ?? undefined,
    mimeType,
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="mb-6 flex w-full justify-end"
    >
      <div className="flex w-full max-w-[88%] flex-row-reverse items-end gap-3 self-end sm:max-w-[75%] md:max-w-[65%]">
        <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-[#1E3A5F] text-white">
          <UserIcon size={16} />
        </div>
        <div className="relative rounded-2xl rounded-br-sm border-2 border-dashed border-[#1E3A5F]/30 bg-[#1E3A5F]/5 px-5 py-3.5 text-[15px] text-slate-700 shadow-sm">
          <button
            type="button"
            onClick={onRemove}
            className="absolute -right-2 -top-2 flex h-6 w-6 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-500 shadow-sm transition-colors hover:text-slate-800"
            title="Retirer le fichier"
          >
            <XIcon size={14} />
          </button>
          <div className="space-y-2">
            <AttachmentPreview attachment={attachment} variant="draft" />
            <p className="text-xs text-slate-500">
              Pièce jointe — ajoute du contexte puis envoie pour analyser.
            </p>
          </div>
        </div>
      </div>
    </motion.div>
  )
}
