"use client"

import { useState, useRef, useEffect } from "react"
import { Send, Bot, User, Sparkles, Copy, Check, AlertTriangle, Scale, Briefcase } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { useToast } from "@/hooks/use-toast"
import ReactMarkdown from "react-markdown"

interface ChatbotProps {
  selectedText: string
  isLoading: boolean
}

type MessageContentType = "text" | "dispute-case" | "dispute-simulation" | "highlighted-clause"

interface DisputeCase {
  id: string
  title: string
  summary: string
  keyPoints: string[]
  judgmentResult: string
  relevance: string
}

interface DisputeSimulation {
  situation: string
  conversation: {
    role: "user" | "consultant"
    content: string
  }[]
}

interface HighlightedClause {
  text: string
  risk: "High" | "Medium" | "Low"
  explanation: string
  precedents: {
    title: string
    summary: string
  }[]
}

interface MessageContent {
  type: MessageContentType
  text?: string
  disputeCase?: DisputeCase
  disputeSimulation?: DisputeSimulation
  highlightedClause?: HighlightedClause
}

interface Message {
  id: string
  role: "user" | "assistant"
  content: MessageContent
}

export function Chatbot({ selectedText, isLoading }: ChatbotProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content: {
        type: "text",
        text: "Hello! I'm your FinanceGuard AI assistant. I can help you understand the financial document and answer any questions you have about it. You can select text from the document to ask specific questions or try these examples:\n\n- What are the risks in this document?\n- Show me dispute cases related to fees\n- Simulate a dispute about early withdrawal penalties\n- Highlight toxic clauses in this document",
      },
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
      content: {
        type: "text",
        text: input,
      },
    }

    setMessages((prev) => [...prev, userMessage])
    setInput("")
    setIsTyping(true)

    // Simulate AI response after a delay
    setTimeout(() => {
      const assistantMessage = generateMockResponse(input)
      setMessages((prev) => [...prev, assistantMessage])
      setIsTyping(false)
    }, 1500)
  }

  const generateMockResponse = (query: string): Message => {
    const lowerQuery = query.toLowerCase()

    // Check for dispute cases query
    if (lowerQuery.includes("dispute") && lowerQuery.includes("case")) {
      return {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: {
          type: "dispute-case",
          text: "I found a relevant dispute case that might be helpful:",
          disputeCase: {
            id: "DC-2023-1045",
            title: "Smith v. Financial Products Corp",
            summary:
              "Investor claimed that fee structure was misrepresented in the product documentation, leading to unexpected charges.",
            keyPoints: [
              "The court found that the fee disclosure was not prominently displayed",
              "The financial institution failed to adequately explain the fee calculation method",
              "The marketing materials emphasized returns without equal emphasis on fees",
            ],
            judgmentResult: "Settled for $1.2M with agreement to revise disclosure documents.",
            relevance: "This case involved similar fee structure language to what appears in your document on page 24.",
          },
        },
      }
    }

    // Check for dispute simulation query
    if (lowerQuery.includes("simulate") || (lowerQuery.includes("dispute") && lowerQuery.includes("withdrawal"))) {
      return {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: {
          type: "dispute-simulation",
          text: "Here's a simulation of how a dispute about early withdrawal penalties might play out:",
          disputeSimulation: {
            situation:
              "You invested in a financial product with a 5-year term, but need to withdraw after 2 years due to unexpected medical expenses. The product has a 5% early withdrawal penalty.",
            conversation: [
              {
                role: "user",
                content:
                  "I need to withdraw my investment early due to medical expenses. The 5% penalty seems excessive given my circumstances. Is there any way to reduce or waive this fee?",
              },
              {
                role: "consultant",
                content:
                  "While the terms clearly state a 5% early withdrawal penalty, there is precedent for waiving or reducing fees in cases of financial hardship due to medical circumstances. You should submit a hardship waiver request with documentation of your medical expenses. In similar cases, financial institutions have reduced penalties to 1-2% or waived them entirely.",
              },
            ],
          },
        },
      }
    }

    // Check for highlight toxic clauses query
    if (lowerQuery.includes("highlight") || lowerQuery.includes("toxic") || lowerQuery.includes("clause")) {
      return {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: {
          type: "highlighted-clause",
          text: "I've identified a potentially concerning clause in the document:",
          highlightedClause: {
            text: "The Company reserves the right to modify any terms of this agreement, including fees and redemption policies, with 30 days notice provided electronically to the email address on file.",
            risk: "High",
            explanation:
              "This clause allows the financial institution to unilaterally change key terms of the agreement, including fees and redemption policies, with minimal notice. The electronic notification requirement may result in missed notifications if emails go to spam folders.",
            precedents: [
              {
                title: "Johnson v. Investment Partners (2021)",
                summary:
                  "Court ruled that unilateral changes to fee structures with only electronic notification was insufficient, especially when resulting in significant financial impact.",
              },
              {
                title: "Regulatory Guidance 2022-03",
                summary:
                  "Financial regulators have indicated that material changes to financial product terms should require affirmative consent, not just notification.",
              },
            ],
          },
        },
      }
    }

    // Default response for general queries
    if (lowerQuery.includes("risk")) {
      return {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: {
          type: "text",
          text: "Based on my analysis, this document contains several risk factors related to market volatility and liquidity constraints. The most significant risk appears in section 3.2, which outlines potential losses due to market fluctuations. I recommend paying close attention to the risk disclosure statements on pages 15-18.",
        },
      }
    } else if (lowerQuery.includes("fee") || lowerQuery.includes("charge")) {
      return {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: {
          type: "text",
          text: "The document mentions several fees: a 1.5% annual management fee, a 0.2% administrative fee, and potential early withdrawal penalties of up to 3%. These fees are detailed in section 4.3 of the document. Compared to industry standards, the management fee is slightly above average for this type of financial product.",
        },
      }
    } else {
      return {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: {
          type: "text",
          text: "I've analyzed your question about the document. To provide a more specific answer, I would need to reference the exact section you're inquiring about. You can select specific text from the document or ask a more detailed question about particular aspects like risks, fees, terms, or dispute resolution processes.",
        },
      }
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

  const renderMessageContent = (message: Message) => {
    const { content } = message

    switch (content.type) {
      case "text":
        return (
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <ReactMarkdown>{content.text || ""}</ReactMarkdown>
          </div>
        )

      case "dispute-case":
        return (
          <div className="space-y-3">
            {content.text && <p>{content.text}</p>}
            {content.disputeCase && (
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base flex items-center gap-2">
                    <Briefcase className="h-4 w-4" />
                    {content.disputeCase.title}
                  </CardTitle>
                  <CardDescription>Case #{content.disputeCase.id}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                  <div>
                    <p className="font-medium mb-1">Summary</p>
                    <p>{content.disputeCase.summary}</p>
                  </div>
                  <div>
                    <p className="font-medium mb-1">Key Points</p>
                    <ul className="list-disc list-inside space-y-1">
                      {content.disputeCase.keyPoints.map((point, index) => (
                        <li key={index}>{point}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <p className="font-medium mb-1">Judgment</p>
                    <p>{content.disputeCase.judgmentResult}</p>
                  </div>
                  <div className="bg-amber-50 p-3 rounded-md border border-amber-200">
                    <p className="font-medium mb-1 text-amber-800">Relevance to Your Document</p>
                    <p className="text-amber-800">{content.disputeCase.relevance}</p>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )

      case "dispute-simulation":
        return (
          <div className="space-y-3">
            {content.text && <p>{content.text}</p>}
            {content.disputeSimulation && (
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base flex items-center gap-2">
                    <Scale className="h-4 w-4" />
                    Dispute Simulation
                  </CardTitle>
                  <CardDescription>How a potential dispute might be resolved</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                  <div className="bg-muted p-3 rounded-md">
                    <p className="font-medium mb-1">Situation</p>
                    <p>{content.disputeSimulation.situation}</p>
                  </div>
                  <div>
                    <p className="font-medium mb-1">Conversation</p>
                    <div className="space-y-3">
                      {content.disputeSimulation.conversation.map((item, index) => (
                        <div
                          key={index}
                          className={`flex gap-2 ${item.role === "consultant" ? "justify-start" : "justify-end"}`}
                        >
                          <div
                            className={`rounded-lg px-3 py-2 max-w-[90%] ${
                              item.role === "consultant" ? "bg-muted" : "bg-primary text-primary-foreground"
                            }`}
                          >
                            <div className="text-xs font-medium mb-1">
                              {item.role === "consultant" ? "Financial Consultant" : "You"}
                            </div>
                            <p>{item.content}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )

      case "highlighted-clause":
        return (
          <div className="space-y-3">
            {content.text && <p>{content.text}</p>}
            {content.highlightedClause && (
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4" />
                    Highlighted Clause
                    <Badge
                      variant="outline"
                      className={`ml-auto ${
                        content.highlightedClause.risk === "High"
                          ? "bg-red-50 text-red-700 border-red-200"
                          : content.highlightedClause.risk === "Medium"
                            ? "bg-amber-50 text-amber-700 border-amber-200"
                            : "bg-green-50 text-green-700 border-green-200"
                      }`}
                    >
                      {content.highlightedClause.risk} Risk
                    </Badge>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                  <div className="bg-muted p-3 rounded-md border-l-4 border-red-500">
                    <p className="italic">"{content.highlightedClause.text}"</p>
                  </div>
                  <div>
                    <p className="font-medium mb-1">Analysis</p>
                    <p>{content.highlightedClause.explanation}</p>
                  </div>
                  <div>
                    <p className="font-medium mb-1">Related Precedents</p>
                    <div className="space-y-2">
                      {content.highlightedClause.precedents.map((precedent, index) => (
                        <div key={index} className="bg-muted/50 p-2 rounded-md">
                          <p className="font-medium text-xs">{precedent.title}</p>
                          <p className="text-xs">{precedent.summary}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )

      default:
        return <p>Unsupported message type</p>
    }
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
                className={`relative group rounded-lg px-3 py-2 max-w-[85%] ${
                  message.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted"
                }`}
              >
                {message.role === "assistant" && (
                  <button
                    onClick={() => {
                      const textContent =
                        message.content.type === "text" ? message.content.text || "" : JSON.stringify(message.content)
                      handleCopyMessage(message.id, textContent)
                    }}
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
                  <div className="text-sm whitespace-pre-wrap">{renderMessageContent(message)}</div>
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

