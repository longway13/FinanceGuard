"use client"

import { useState, useRef, useEffect } from "react"
import { Send, Bot, User, Sparkles, Copy, Check } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { ScrollArea } from "@/components/ui/scroll-area"
import { useToast } from "@/hooks/use-toast"

interface ChatbotProps {
  selectedText: string
  isLoading: boolean
}

interface Message {
  id: string
  role: "user" | "assistant"
  content: string
}

export function Chatbot({ selectedText, isLoading }: ChatbotProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content:
        "Hello! I'm your FinanceGuard AI assistant. I can help you understand the financial document and answer any questions you have about it. You can select text from the document to ask specific questions.",
    },
  ])
  const [input, setInput] = useState("")
  const [isTyping, setIsTyping] = useState(false)
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const { toast } = useToast()

  // Update input when text is selected from PDF
  useEffect(() => {
    if (selectedText) {
      setInput(selectedText)
      if (inputRef.current) {
        inputRef.current.focus()
      }
    }
  }, [selectedText])

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const handleSendMessage = async () => {
    if (!input.trim()) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input,
    }

    setMessages((prev) => [...prev, userMessage])
    setInput("")
    setIsTyping(true)

    // Simulate AI response after a delay
    setTimeout(() => {
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: generateMockResponse(input),
      }
      setMessages((prev) => [...prev, assistantMessage])
      setIsTyping(false)
    }, 1500)
  }

  const generateMockResponse = (query: string): string => {
    // Simple mock responses based on keywords in the query
    if (query.toLowerCase().includes("risk")) {
      return "Based on my analysis, this document contains several risk factors related to market volatility and liquidity constraints. The most significant risk appears in section 3.2, which outlines potential losses due to market fluctuations. I recommend paying close attention to the risk disclosure statements on pages 15-18."
    } else if (query.toLowerCase().includes("fee") || query.toLowerCase().includes("charge")) {
      return "The document mentions several fees: a 1.5% annual management fee, a 0.2% administrative fee, and potential early withdrawal penalties of up to 3%. These fees are detailed in section 4.3 of the document. Compared to industry standards, the management fee is slightly above average for this type of financial product."
    } else if (query.toLowerCase().includes("dispute") || query.toLowerCase().includes("legal")) {
      return "The dispute resolution process is outlined in section 7.1. It requires mandatory arbitration through the Financial Industry Regulatory Authority (FINRA). This means you would waive your right to a jury trial in the event of a dispute. This is a common but important clause to be aware of."
    } else {
      return "I've analyzed your question about the document. To provide a more specific answer, I would need to reference the exact section you're inquiring about. You can select specific text from the document or ask a more detailed question about particular aspects like risks, fees, terms, or dispute resolution processes."
    }
  }

  const handleCopyMessage = (id: string, content: string) => {
    navigator.clipboard.writeText(content)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 2000)

    toast({
      title: "Copied to clipboard",
      description: "The message has been copied to your clipboard",
    })
  }

  if (isLoading) {
    return (
      <div className="flex flex-col h-full">
        <div className="flex-1 p-4">
          <div className="space-y-4">
            <div className="flex gap-3">
              <Skeleton className="h-10 w-10 rounded-full" />
              <div className="space-y-2">
                <Skeleton className="h-4 w-40" />
                <Skeleton className="h-16 w-64" />
              </div>
            </div>
          </div>
        </div>
        <div className="border-t p-4">
          <Skeleton className="h-10 w-full" />
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      <ScrollArea className="flex-1 p-4">
        <div className="space-y-4">
          {messages.map((message) => (
            <div key={message.id} className={`flex gap-3 ${message.role === "user" ? "justify-end" : ""}`}>
              {message.role === "assistant" && (
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary/10">
                  <Bot className="h-5 w-5 text-primary" />
                </div>
              )}
              <div
                className={`relative group rounded-lg px-3 py-2 max-w-[80%] ${
                  message.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted"
                }`}
              >
                {message.role === "assistant" && (
                  <button
                    onClick={() => handleCopyMessage(message.id, message.content)}
                    className="absolute right-2 top-2 opacity-0 group-hover:opacity-100 transition-opacity"
                    aria-label="Copy message"
                  >
                    {copiedId === message.id ? (
                      <Check className="h-4 w-4 text-green-500" />
                    ) : (
                      <Copy className="h-4 w-4 text-muted-foreground" />
                    )}
                  </button>
                )}
                <div className="space-y-1">
                  <div className="text-xs font-medium">{message.role === "user" ? "You" : "FinanceGuard AI"}</div>
                  <div className="text-sm whitespace-pre-wrap">{message.content}</div>
                </div>
              </div>
              {message.role === "user" && (
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary">
                  <User className="h-5 w-5 text-primary-foreground" />
                </div>
              )}
            </div>
          ))}
          {isTyping && (
            <div className="flex gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary/10">
                <Bot className="h-5 w-5 text-primary" />
              </div>
              <div className="rounded-lg px-3 py-2 bg-muted max-w-[80%]">
                <div className="space-y-1">
                  <div className="text-xs font-medium">FinanceGuard AI</div>
                  <div className="flex items-center gap-1">
                    <div className="h-2 w-2 rounded-full bg-primary animate-bounce" />
                    <div className="h-2 w-2 rounded-full bg-primary animate-bounce [animation-delay:0.2s]" />
                    <div className="h-2 w-2 rounded-full bg-primary animate-bounce [animation-delay:0.4s]" />
                  </div>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </ScrollArea>
      <div className="border-t p-4">
        <form
          onSubmit={(e) => {
            e.preventDefault()
            handleSendMessage()
          }}
          className="flex items-center gap-2"
        >
          <Input
            ref={inputRef}
            placeholder="Ask about the document or selected text..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            className="flex-1"
          />
          <Button type="submit" size="icon" disabled={!input.trim() || isTyping}>
            {isTyping ? <Sparkles className="h-5 w-5 animate-pulse" /> : <Send className="h-5 w-5" />}
            <span className="sr-only">Send message</span>
          </Button>
        </form>
      </div>
    </div>
  )
}

