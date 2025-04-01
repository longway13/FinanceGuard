"use client"

import { useState, useEffect } from "react"
import { ChevronLeft, ChevronRight, Search, ZoomIn, ZoomOut } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { useToast } from "@/hooks/use-toast"
import { Document, Page } from 'react-pdf';
import { pdfjs } from 'react-pdf';

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString();

interface PdfViewerProps {
  fileId: string
  onTextSelect: (text: string) => void
  isLoading: boolean
}

export function PdfViewer({ fileId, onTextSelect, isLoading }: PdfViewerProps) {
  const [numPages, setNumPages] = useState<number>();
  const [pageNumber, setPageNumber] = useState(1)
  const [totalPages, setTotalPages] = useState(10) // Mock total pages
  const [scale, setScale] = useState(1.0)
  const [searchText, setSearchText] = useState("")
  const [isLoadingPdf, setIsLoadingPdf] = useState(true)
  const { toast } = useToast()

  // 파일 ID에 따라 로드할 PDF URL 결정
  const pdfUrl = fileId.startsWith("sample_")
    ? "/sample/example.pdf" // public/sample 폴더 내에 있는 mock PDF 파일
    : `/api/pdf/${fileId}`  // 추후 실제 파일 경로를 처리할 API 엔드포인트

  useEffect(() => {
    // fileId 변경 시 상태 초기화
    setIsLoadingPdf(true)

    // PDF 로딩 시뮬레이션 (실제 구현 시 PDF 로더 사용)
    const timer = setTimeout(() => {
      setIsLoadingPdf(false)

      // 모의 데이터를 위한 페이지 수 설정
      if (fileId.startsWith("sample_")) {
        setTotalPages(15)
      }

      toast({
        title: "Document loaded",
        description: "Financial document has been loaded successfully",
      })
    }, 1500)

    return () => clearTimeout(timer)
  }, [fileId, toast])

  const handlePreviousPage = () => {
    setPageNumber((prevPageNumber) => Math.max(prevPageNumber - 1, 1))
    // 실제 구현 시 PDF 뷰어의 페이지 이동 제어
  }

  const handleNextPage = () => {
    setPageNumber((prevPageNumber) => Math.min(prevPageNumber + 1, totalPages))
    // 실제 구현 시 PDF 뷰어의 페이지 이동 제어
  }

  const handleZoomIn = () => {
    setScale((prevScale) => Math.min(prevScale + 0.2, 3))
    // 실제 구현 시 PDF 뷰어의 줌 제어
  }

  const handleZoomOut = () => {
    setScale((prevScale) => Math.max(prevScale - 0.2, 0.6))
    // 실제 구현 시 PDF 뷰어의 줌 제어
  }

  const handleTextSelection = () => {
    // 실제 구현 시 PDF 뷰어에서 선택한 텍스트 가져오기
    const financialTerms = [
      "The annual management fee is 1.5% of assets under management.",
      "Early redemption penalties apply for withdrawals within the first 3 years.",
      "Market risk may result in substantial loss of principal.",
      "This product is not FDIC insured and may lose value.",
      "The liquidity of this investment is limited, with quarterly redemption windows.",
      "Performance fees of 20% apply to returns above the benchmark.",
    ]

    const selectedText = financialTerms[Math.floor(Math.random() * financialTerms.length)]
    onTextSelect(selectedText)

    toast({
      title: "Text selected",
      description: "The selected text has been added to the chatbot",
    })
  }

  const handleSearch = () => {
    if (!searchText) return

    toast({
      title: "Searching document",
      description: `Searching for "${searchText}" in the document`,
    })

    // 실제 구현 시 PDF 내 텍스트 검색 처리
  }
  

  if (isLoading || isLoadingPdf) {
    return (
      <div className="flex flex-col h-full">
        <div className="flex items-center justify-between p-2 border-b">
          <div className="flex items-center space-x-2">
            <Skeleton className="h-8 w-8 rounded-md" />
            <Skeleton className="h-8 w-8 rounded-md" />
          </div>
          <div className="flex items-center space-x-2">
            <Skeleton className="h-8 w-24 rounded-md" />
          </div>
          <div className="flex items-center space-x-2">
            <Skeleton className="h-8 w-8 rounded-md" />
            <Skeleton className="h-8 w-8 rounded-md" />
            <Skeleton className="h-8 w-8 rounded-md" />
          </div>
        </div>
        <div className="flex-1 flex items-center justify-center bg-muted/20">
          <div className="text-center space-y-4">
            <Skeleton className="h-[400px] w-[300px] mx-auto" />
            <p className="text-muted-foreground">Loading document...</p>
          </div>
        </div>
      </div>
    )
  }
  function onDocumentLoadSuccess({ numPages }: { numPages: number }): void {
    setNumPages(numPages);
  }
  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between p-2 border-b">
        <div className="flex items-center space-x-2">
          <Button variant="outline" size="icon" onClick={handlePreviousPage} disabled={pageNumber <= 1}>
            <ChevronLeft className="h-4 w-4" />
            <span className="sr-only">Previous page</span>
          </Button>
          <Button variant="outline" size="icon" onClick={handleNextPage} disabled={pageNumber >= totalPages}>
            <ChevronRight className="h-4 w-4" />
            <span className="sr-only">Next page</span>
          </Button>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-sm">
            Page {pageNumber} of {totalPages}
          </span>
        </div>
        <div className="flex items-center space-x-2">
          <Button variant="outline" size="icon" onClick={handleZoomOut}>
            <ZoomOut className="h-4 w-4" />
            <span className="sr-only">Zoom out</span>
          </Button>
          <Button variant="outline" size="icon" onClick={handleZoomIn}>
            <ZoomIn className="h-4 w-4" />
            <span className="sr-only">Zoom in</span>
          </Button>
          <div className="relative">
            <Input
              type="text"
              placeholder="Search..."
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              className="h-8 w-32 pl-8"
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            />
            <Search className="absolute left-2 top-2 h-4 w-4 text-muted-foreground" />
          </div>
        </div>
      </div>
      <div className="flex-1 overflow-hidden bg-muted/20 flex justify-center" onClick={handleTextSelection}>
        <div>
        <Document file={pdfUrl} onLoadSuccess={onDocumentLoadSuccess}>
          <Page pageNumber={pageNumber} />
        </Document>
        <p>
          Page {pageNumber} of {numPages}
        </p>
      </div>
      </div>
    </div>
  )
}
