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
import { useAppContext } from "@/lib/context"

export function Dashboard({ fileId, fileUrl }: { fileId: string; fileUrl?: string }) {
  const [selectedText, setSelectedText] = useState("")
  const [pdfUrl, setPdfUrl] = useState<string | undefined>(undefined)
  const [documentData, setDocumentData] = useState({
    overview: {
      summary: "",
      keyMetrics: {
        annualReturn: "-",
        volatility: "-",
        managementFee: "-",
        minimumInvestment: "-",
        lockupPeriod: "-",
        riskLevel: "보통위험" as const,
      },
      keyFindings: [],
      recommendations: []
    },
    disputes: {
      cases: [],
      totalCases: 0,
      trendData: []
    }
  })
  const [isLoading, setIsLoading] = useState(true)
  const { toast } = useToast()
  const { activeTab, setActiveTab, selectedDisputeId } = useAppContext()

  useEffect(() => {
    const loadData = () => {
      setIsLoading(true)
      try {
        // URL에서 파라미터 추출
        const urlParams = new URLSearchParams(window.location.search)
        const summary = urlParams.get('summary') || ""
        const keyValues = JSON.parse(urlParams.get('keyValues') || "{}")
        const keyFindings = JSON.parse(urlParams.get('keyFindings') || "[]")
        
        // documentData 설정
        setDocumentData({
          overview: {
            summary,
            keyMetrics: {
              annualReturn: keyValues.annualReturn || "-",
              volatility: keyValues.volatility || "-",
              managementFee: keyValues.managementFee || "-",
              minimumInvestment: keyValues.minimumInvestment || "-",
              lockupPeriod: keyValues.lockupPeriod || "-",
              riskLevel: keyValues.riskLevel || "보통위험",
            },
            keyFindings,
            recommendations: []
          },
          disputes: {
            cases: [],
            totalCases: 0,
            trendData: []
          }
        })
      } catch (error) {
        console.error('Error parsing URL parameters:', error)
        toast({
          title: "Error loading document",
          description: "There was an error loading the document data. Please try again.",
          variant: "destructive",
        })
      } finally {
        setIsLoading(false)
      }
    }

    if (typeof window !== 'undefined') {
      loadData()
    }
  }, [toast])

  useEffect(() => {
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
        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex flex-col h-full">
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
              <DisputeCases data={documentData.disputes} isLoading={isLoading} selectedId={selectedDisputeId} />
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

