import { motion } from 'framer-motion'
import { BotIcon, UserIcon } from 'lucide-react'

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
        className={`flex max-w-[85%] items-end gap-3 md:max-w-[75%] ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
      >
        <div
          className={`flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full ${isUser ? 'bg-[#1E3A5F] text-white' : 'border border-slate-200 bg-[#F1F5F9] text-slate-600'}`}
        >
          {isUser ? <UserIcon size={16} /> : <BotIcon size={16} />}
        </div>
        <div
          className={`rounded-2xl px-5 py-3.5 text-[15px] leading-relaxed ${isUser ? 'rounded-br-sm bg-[#1E3A5F] font-medium text-white shadow-sm' : 'rounded-bl-sm border border-slate-200/80 bg-[#F1F5F9] text-slate-700'}`}
        >
          {message.content}
        </div>
      </div>
    </motion.div>
  )
}
