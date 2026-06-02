import { motion } from 'framer-motion'
import { BotIcon, UserIcon } from 'lucide-react'
import ReactMarkdown from 'react-markdown'

export type Message = {
  id: string
  role: 'user' | 'agent'
  content: string
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
            <span className="whitespace-pre-wrap">{message.content}</span>
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
