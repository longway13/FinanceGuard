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
import { BackendResponse } from '@/types/chat'

interface ChatbotProps {
  selectedText: string
  isLoading: boolean
}

type MessageContentType = "text" | "dispute-cases" | "simulation" | "highlighted-clause" | "dispute-case" | "dispute-simulation" | "risky_clause"

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
//Risky_Commnents Interface Definition
interface Risky_Clause {
  text: string,
  risk: string,
  similarity: number
}


interface MessageContent {
  type: MessageContentType
  text?: string
  disputeCase?: DisputeCase
  disputeSimulation?: DisputeSimulation
  highlightedClause?: HighlightedClause
  risky_clause?: Risky_Clause
}

interface Message {
  id: string
  role: "user" | "assistant"
  content: MessageContent
}

export function Chatbot({ selectedText, isLoading }: ChatbotProps) {
  
  // System Intro Message
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content: {
        type: "text",
        text: `<div class="welcome-message">
<div class="welcome-header">
<h3>안녕하세요! 저는 여러분의 FinanceGuard AI 어시스턴트입니다.</h3>
<p>저희 서비스는 금융상품 문서를 쉽게 이해할 수 있도록 도와드리며, 특히 금융상품에 내재된 위험성을 파악하는 데 중점을 두고 있습니다.</p>
</div>
<div class="example-questions">
<h4>💡 다음과 같은 질문들을 해보세요</h4>
<ul>
<li><span class="tag risk">위험</span> 이 문서에 나타난 주요 위험 요소는 무엇인가요?</li>
<li><span class="tag case">판례</span> 수수료와 관련된 분쟁 사례를 보여주세요.</li>
<li><span class="tag simulation">시뮬레이션</span> 조기 인출 벌금에 대한 분쟁을 시뮬레이션 해주세요.</li>
<li><span class="tag highlight">조항</span> 유해한 조항을 하이라이트 해주세요.</li>
</ul>
</div>
<div class="welcome-footer">
<p>이러한 정보를 통해 금융상품 구매 전에 잠재적 리스크를 명확하게 파악하고, 보다 안전한 투자 결정을 내리실 수 있도록 지원합니다.</p>
</div>
</div>`,
      },
    },
  ])

  // User Input
  const [input, setInput] = useState("")
  const [isTyping, setIsTyping] = useState(false)
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const { toast } = useToast()

  // Update input when text is selected from PDF (아직 구현 안함.)
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

    try {
      // 백엔드 API 호출
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: input }),
      });

      if (!response.ok) {
        throw new Error('서버 응답 오류');
      }

      const backendResponse: BackendResponse = await response.json();
      let assistantMessage: Message;
      
      // 백엔드 응답 타입에 따라 메시지 생성
      switch (backendResponse.type) {
        case 'simple_dialogue':
          assistantMessage = {
            id: Date.now().toString(),
            role: "assistant",
            content: {
              type: "text",
              text: backendResponse.response,
            },
          };
          break;
          
        case 'simulation':
          assistantMessage = {
            id: Date.now().toString(),
            role: "assistant",
            content: {
              type: "dispute-simulation",
              text: "Here's a simulation of how a dispute might play out:",
              disputeSimulation: {
                situation: backendResponse.simulations[0].situation,
                conversation: backendResponse.simulations.flatMap(sim => [
                  {
                    role: "user",
                    content: sim.user,
                  },
                  {
                    role: "consultant",
                    content: sim.agent,
                  },
                ]),
              },
            },
          };
          break;
          
        case 'cases':
          assistantMessage = {
            id: Date.now().toString(),
            role: "assistant",
            content: {
              type: "dispute-case",
              text: "I found a relevant dispute case that might be helpful:",
              disputeCase: {
                id: `DC-${Date.now()}`,
                title: backendResponse.response.title,
                summary: backendResponse.response.summary,
                keyPoints: backendResponse.response['key points'].split('\n'),
                judgmentResult: backendResponse.response['judge result'],
                relevance: "This case is relevant to your query.",
              },
            },
          };
          break;
          
        default:
          assistantMessage = {
            id: Date.now().toString(),
            role: "assistant",
            content: {
              type: "text",
              text: "응답을 받았지만 처리할 수 없는 형식입니다. 다시 시도해 주세요.",
            },
          };
      }
      
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error:', error);
      // 에러 메시지 추가
      const errorMessage: Message = {
        id: Date.now().toString(),
        role: "assistant",
        content: {
          type: "text",
          text: "죄송합니다. 요청을 처리하는 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
        },
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsTyping(false);
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
        // 환영 메시지인 경우 HTML로 직접 렌더링
        if (content.text?.includes('<div class="welcome-message">')) {
          return (
            <div 
              className="prose prose-sm prose-p:my-0.5 prose-headings:my-0.5 prose-ul:my-0.5 prose-li:my-0 dark:prose-invert max-w-none leading-tight"
              dangerouslySetInnerHTML={{ 
                __html: content.text
                  .replace('class="welcome-message"', 'class="bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-gray-800 dark:to-gray-700 rounded-lg p-1.5 shadow-sm"')
                  .replace('class="welcome-header"', 'class="mb-0"')
                  .replace('class="example-questions"', 'class="bg-white dark:bg-gray-800 rounded-lg p-1 shadow-sm mb-0 mt-0"')
                  .replace('class="welcome-footer"', 'class="text-sm text-gray-600 dark:text-gray-300 italic mt-0"')
                  .replace(/<h3>/g, '<h3 class="text-base font-semibold mb-0 mt-0 text-primary leading-none">')
                  .replace(/<h4>/g, '<h4 class="text-sm font-medium mb-0 mt-0 flex items-center leading-none">')
                  .replace(/<p>/g, '<p class="leading-none mb-0 mt-0">')
                  .replace(/><p>/g, '><p class="mt-0">')
                  .replace(/<ul>/g, '<ul class="my-0 pl-0 space-y-0">')
                  .replace(/<li>/g, '<li class="flex items-start my-0 leading-none">')
                  .replace(/class="tag risk"/g, 'class="inline-block mr-1 px-1 bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100 text-xs font-medium rounded"')
                  .replace(/class="tag case"/g, 'class="inline-block mr-1 px-1 bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100 text-xs font-medium rounded"')
                  .replace(/class="tag simulation"/g, 'class="inline-block mr-1 px-1 bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100 text-xs font-medium rounded"')
                  .replace(/class="tag highlight"/g, 'class="inline-block mr-1 px-1 bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-100 text-xs font-medium rounded"')
              }} 
            />
          )
        }
        
        // 일반 텍스트 메시지는 ReactMarkdown으로 렌더링
        return (
          <div className="prose prose-sm prose-p:my-0.5 prose-headings:my-0.5 prose-ul:my-0.5 prose-li:my-0 dark:prose-invert max-w-none leading-tight">
            <ReactMarkdown>
              {content.text || ""}
            </ReactMarkdown>
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

