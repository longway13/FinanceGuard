"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { CheckCircle, Info, TrendingUp, TrendingDown, Percent, Calendar, DollarSign } from "lucide-react"
import ReactMarkdown from "react-markdown"

interface OverviewProps {
  data?: {
    summary: string
    keyMetrics: {
      annualReturn: string
      volatility: string
      managementFee: string
      minimumInvestment: string
      lockupPeriod: string
      riskLevel: "매우높은위험" | "높은위험" | "보통위험" | "낮은위험" | "매우낮은위험"
    }
    keyFindings: string[]
    recommendations: string[]
  }
  isLoading: boolean
}

export function Overview({ data, isLoading }: OverviewProps) {
  const [activeTab, setActiveTab] = useState("summary")

  // Provide default values if data is undefined
  const safeData = data || {
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
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-3/4" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-40 w-full" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
        </div>
      </div>
    )
  }

  const getRiskBadge = (riskLevel: string) => {
    switch (riskLevel) {
      case "매우높은위험":
        return <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200">매우 높은 위험</Badge>
      case "높은위험":
        return <Badge variant="outline" className="bg-orange-50 text-orange-700 border-orange-200">높은 위험</Badge>
      case "보통위험":
        return <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200">보통 위험</Badge>
      case "낮은위험":
        return <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">낮은 위험</Badge>
      case "매우낮은위험":
        return <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">매우 낮은 위험</Badge>
      default:
        return <Badge variant="outline">알 수 없음</Badge>
    }
  }

  // Sample markdown content for demonstration
  const markdownContent =
    safeData.summary ||
    `
  # Financial Product Overview

  This investment product is a **structured note** with principal protection and market-linked returns. 
  
  ## Key Features
  
  * 100% principal protection at maturity
  * Returns linked to S&P 500 performance
  * 5-year investment term
  * Semi-annual interest payments
  
  ## Risk Considerations
  
  The product carries moderate risk due to:
  
  1. Market risk affecting potential returns
  2. Liquidity constraints during the investment term
  3. Credit risk of the issuing institution
  
  > Note: Principal protection applies only if held to maturity.
  `

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Financial Product Overview</h2>
        <p className="text-muted-foreground">Comprehensive analysis of the financial document</p>
      </div>

      <Tabs defaultValue="summary" value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList>
          <TabsTrigger value="summary">Summary</TabsTrigger>
          <TabsTrigger value="metrics">Key Metrics</TabsTrigger>
          <TabsTrigger value="findings">Key Findings</TabsTrigger>
        </TabsList>

        <TabsContent value="summary" className="space-y-4">
          <Card>
            <CardContent className="pt-6">
              <div className="prose prose-sm dark:prose-invert max-w-none">
                <ReactMarkdown>{markdownContent}</ReactMarkdown>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="metrics" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>Financial Metrics</span>
                {getRiskBadge(safeData.keyMetrics.riskLevel)}
              </CardTitle>
              <CardDescription>Key performance and fee metrics for this financial product</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="flex flex-col space-y-1.5 p-4 border rounded-lg">
                  <div className="flex items-center gap-2">
                    <TrendingUp className="h-4 w-4 text-green-500" />
                    <span className="text-sm font-medium">Annual Return</span>
                  </div>
                  <div className="text-2xl font-bold">{safeData.keyMetrics.annualReturn}</div>
                  <div className="text-xs text-muted-foreground">Expected return</div>
                </div>

                <div className="flex flex-col space-y-1.5 p-4 border rounded-lg">
                  <div className="flex items-center gap-2">
                    <TrendingDown className="h-4 w-4 text-amber-500" />
                    <span className="text-sm font-medium">Volatility</span>
                  </div>
                  <div className="text-2xl font-bold">{safeData.keyMetrics.volatility}</div>
                  <div className="text-xs text-muted-foreground">Risk indicator</div>
                </div>

                <div className="flex flex-col space-y-1.5 p-4 border rounded-lg">
                  <div className="flex items-center gap-2">
                    <Percent className="h-4 w-4 text-blue-500" />
                    <span className="text-sm font-medium">Management Fee</span>
                  </div>
                  <div className="text-2xl font-bold">{safeData.keyMetrics.managementFee}</div>
                  <div className="text-xs text-muted-foreground">Annual fee</div>
                </div>

                <div className="flex flex-col space-y-1.5 p-4 border rounded-lg">
                  <div className="flex items-center gap-2">
                    <DollarSign className="h-4 w-4 text-primary" />
                    <span className="text-sm font-medium">Minimum Investment</span>
                  </div>
                  <div className="text-2xl font-bold">{safeData.keyMetrics.minimumInvestment}</div>
                  <div className="text-xs text-muted-foreground">Initial investment</div>
                </div>

                <div className="flex flex-col space-y-1.5 p-4 border rounded-lg">
                  <div className="flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-purple-500" />
                    <span className="text-sm font-medium">Lockup Period</span>
                  </div>
                  <div className="text-2xl font-bold">{safeData.keyMetrics.lockupPeriod}</div>
                  <div className="text-xs text-muted-foreground">Minimum holding period</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="findings" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Key Findings</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {safeData.keyFindings.map((finding, index) => (
                    <li key={index} className="flex items-start gap-2">
                      <Info className="h-5 w-5 text-primary shrink-0 mt-0.5" />
                      <span className="text-sm">{finding}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Recommendations</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {safeData.recommendations.map((recommendation, index) => (
                    <li key={index} className="flex items-start gap-2">
                      <CheckCircle className="h-5 w-5 text-green-500 shrink-0 mt-0.5" />
                      <span className="text-sm">{recommendation}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}

