import { useState } from 'react'
import { Sidebar } from './components/Sidebar'
import { ChatArea } from './components/ChatArea'
import type { Message } from './components/MessageBubble'

export function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [restDay, setRestDay] = useState('None')
  const [durationMin, setDurationMin] = useState(60)

  const handleNewChat = () => {
    setMessages([])
  }

  return (
    <div className="flex h-screen w-full overflow-hidden bg-white font-sans selection:bg-blue-500/20">
      <Sidebar
        onNewChat={handleNewChat}
        restDay={restDay}
        setRestDay={setRestDay}
        durationMin={durationMin}
        setDurationMin={setDurationMin}
      />
      <main className="flex min-h-0 min-w-0 flex-1 flex-col">
      <ChatArea
        messages={messages}
        setMessages={setMessages}
        restDay={restDay}
        durationMin={durationMin}
      />
      </main>
    </div>
  )
}
