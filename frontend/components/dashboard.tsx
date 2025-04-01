"use client"

import { useState, useEffect } from "react"
import { PdfViewer } from "@/components/pdf-viewer"
import { RiskAnalysis } from "@/components/risk-analysis"
import { DisputeCases } from "@/components/dispute-cases"
import { Chatbot } from "@/components/chatbot"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useToast } from "@/hooks/use-toast"
import { mockDocumentData } from "@/lib/mock-data"

export function Dashboard({ fileId }: { fileId: string }) {
  const [selectedText, setSelectedText] = useState("")
  const [documentData, setDocumentData] = useState({
    riskAnalysis: {
      overallRisk: 0,
      riskScores: [],
      keyFindings: [],
      recommendations: [],
    },
    disputeCases: {
      cases: [],
      totalCases: 0,
      trendData: [],
    },
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
        setDocumentData(mockDocumentData)
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

  const handleTextSelection = (text: string) => {
    setSelectedText(text)
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="h-[calc(100vh-8rem)] overflow-hidden rounded-lg border border-border">
        <PdfViewer fileId={fileId} onTextSelect={handleTextSelection} isLoading={isLoading} />
      </div>
      <div className="flex flex-col h-[calc(100vh-8rem)] overflow-hidden">
        <Tabs defaultValue="risk" className="flex-1 flex flex-col">
          <TabsList className="grid grid-cols-3">
            <TabsTrigger value="risk">Risk Analysis</TabsTrigger>
            <TabsTrigger value="disputes">Dispute Cases</TabsTrigger>
            <TabsTrigger value="chat">AI Assistant</TabsTrigger>
          </TabsList>
          <TabsContent value="risk" className="flex-1 overflow-auto p-4 border rounded-b-lg">
            <RiskAnalysis data={documentData.riskAnalysis} isLoading={isLoading} />
          </TabsContent>
          <TabsContent value="disputes" className="flex-1 overflow-auto p-4 border rounded-b-lg">
            <DisputeCases data={documentData.disputeCases} isLoading={isLoading} />
          </TabsContent>
          <TabsContent value="chat" className="flex-1 overflow-hidden p-4 border rounded-b-lg flex flex-col">
            <Chatbot selectedText={selectedText} isLoading={isLoading} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}

