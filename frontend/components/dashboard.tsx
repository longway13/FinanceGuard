"use client"

import { useState, useEffect } from "react"
import { PdfViewer } from "@/components/pdf-viewer"
import { Overview } from "@/components/overview"
import { DisputeCases } from "@/components/dispute-cases"
import { Chatbot } from "@/components/chatbot"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useToast } from "@/hooks/use-toast"
import { mockDocumentData } from "@/lib/mock-data"
import type { DisputeCase } from "@/lib/types"

export function Dashboard({ fileId, fileUrl }: { fileId: string; fileUrl?: string }) {
  const [selectedText, setSelectedText] = useState("")
  const [pdfUrl, setPdfUrl] = useState<string | undefined>(undefined)
  const [documentData, setDocumentData] = useState({
    overview: {
      summary: "This is a sample summary of the financial product...",
      keyMetrics: {
        annualReturn: 8.5,
        volatility: 12.3,
        managementFee: 1.5,
        minimumInvestment: 10000,
        lockupPeriod: 12,
        riskLevel: "Medium" as const,
      },
      keyFindings: [
        "Finding 1",
        "Finding 2",
        "Finding 3"
      ],
      recommendations: [
        "Recommendation 1",
        "Recommendation 2"
      ]
    },
    disputes: {
      cases: [
        {
          id: "1",
          title: "Case 1",
          status: "Resolved",
          date: "2024-01-01",
          jurisdiction: "Korea",
          summary: "Summary 1",
          keyIssues: ["Issue 1", "Issue 2"],
          outcome: "Settled",
          relevance: "This case is relevant to your document because..."
        }
      ],
      totalCases: 1,
      trendData: [
        { month: "Jan", count: 5 },
        { month: "Feb", count: 3 }
      ]
    }
  })
  const [isLoading, setIsLoading] = useState(true)
  const { toast } = useToast()

  useEffect(() => {
    // In a real application, you would fetch the document data from your API
    // For demo purposes, we'll simulate loading the data after a delay
    const loadData = async () => {
      setIsLoading(true)
      try {
        // Simulate API call
        await new Promise((resolve) => setTimeout(resolve, 1500))
        setDocumentData({
          overview: mockDocumentData.overview,
          disputes: mockDocumentData.disputeCases,
        })
      } catch (error) {
        toast({
          title: "Error loading document",
          description: "There was an error loading the document data. Please try again.",
          variant: "destructive",
        })
      } finally {
        setIsLoading(false)
      }
    }

    loadData()
  }, [fileId, toast])

  useEffect(() => {
    // PDF URL 설정
    if (fileUrl) {
      setPdfUrl(fileUrl)
    }
  }, [fileUrl])

  const handleTextSelection = (text: string) => {
    setSelectedText(text)
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="h-[calc(100vh-8rem)] overflow-hidden rounded-lg border border-border">
        <PdfViewer fileId={fileId} onTextSelect={handleTextSelection} isLoading={isLoading} url={pdfUrl} />
      </div>
      <div className="flex flex-col h-[calc(100vh-8rem)] overflow-hidden rounded-lg border border-border">
        <Tabs defaultValue="overview" className="flex flex-col h-full">
          <TabsList className="w-full justify-start border-b">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="disputes">Disputes</TabsTrigger>
            <TabsTrigger value="chat">AI Assistant</TabsTrigger>
          </TabsList>
          <div className="flex-1 overflow-hidden">
            <TabsContent value="overview" className="h-full overflow-auto">
              <Overview data={documentData.overview} isLoading={isLoading} />
            </TabsContent>
            <TabsContent value="disputes" className="h-full overflow-auto">
              <DisputeCases data={documentData.disputes} isLoading={isLoading} />
            </TabsContent>
            <TabsContent value="chat" className="h-full overflow-hidden">
              <Chatbot selectedText={selectedText} isLoading={isLoading} />
            </TabsContent>
          </div>
        </Tabs>
      </div>
    </div>
  )
}

