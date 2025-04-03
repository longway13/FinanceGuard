"use client"

import { useState } from "react"
import { Document, Page, pdfjs } from "react-pdf"
import "react-pdf/dist/esm/Page/AnnotationLayer.css"
import "react-pdf/dist/esm/Page/TextLayer.css"
import { Skeleton } from "@/components/ui/skeleton"
import { useToast } from "@/hooks/use-toast"

// PDF.js worker 설정
pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`

interface PdfViewerProps {
  fileId: string
  onTextSelect?: (text: string) => void
  isLoading?: boolean
  url?: string
}

// 하이라이트할 키워드 정의
const HIGHLIGHT_KEYWORDS = ["외화로 투자되는 상품은 15시까지입니다."]

export function PdfViewer({ fileId, onTextSelect, isLoading, url }: PdfViewerProps) {
  const [numPages, setNumPages] = useState<number>(0)
  const [pageNumber, setPageNumber] = useState<number>(1)
  const [highlights, setHighlights] = useState<
    Array<{
      text: string
      page: number
      position: { x: number; y: number }
      width: number
      height: number
    }>
  >([])
  const { toast } = useToast()

  // PDF 로드 시 텍스트 검색 및 하이라이트
  const onDocumentLoadSuccess = async ({ numPages }: { numPages: number }) => {
    setNumPages(numPages)

    const newHighlights: Array<{
      text: string
      page: number
      position: { x: number; y: number }
      width: number
      height: number
    }> = []

    for (let i = 1; i <= numPages; i++) {
      const page = await pdfjs.getDocument(url!).promise.then((doc) => doc.getPage(i))

      // 먼저 scale 1로 viewport를 받아 실제 PDF 너비를 확인
      const initialViewport = page.getViewport({ scale: 1 })
      // <Page>에서 width={800}으로 렌더링하므로, scale factor 계산
      const scale = 800 / initialViewport.width
      // 동일한 scale을 적용하여 viewport 생성
      const viewport = page.getViewport({ scale })

      const textContent = await page.getTextContent()

      // 각 키워드에 대해 검색
      HIGHLIGHT_KEYWORDS.forEach((keyword) => {
        textContent.items.forEach((item: any) => {
          if (item.str.includes(keyword)) {
            const transform = item.transform

            // scale을 적용해 텍스트의 위치와 크기 계산
            const x = transform[4] * scale
            const textHeight = (item.height || 20) * scale
            const y = viewport.height - transform[5] * scale - textHeight
            const textWidth = item.width * scale

            newHighlights.push({
              text: keyword,
              page: i,
              position: { x, y },
              width: textWidth,
              height: textHeight,
            })
          }
        })
      })
    }

    setHighlights(newHighlights)
  }

  if (isLoading) {
    return (
      <div className="w-full h-full rounded-lg border">
        <Skeleton className="w-full h-full" />
      </div>
    )
  }

  if (!url) {
    return (
      <div className="w-full h-full rounded-lg border flex items-center justify-center">
        <p className="text-muted-foreground">No PDF document loaded</p>
      </div>
    )
  }

  return (
    <div className="w-full h-full flex flex-col">
      <div className="flex items-center justify-between p-4 border-b">
        <h2 className="text-lg font-semibold">Finance Product PDF</h2>
      </div>

      <div className="w-full h-full rounded-lg border relative overflow-auto">
        <Document
          file={url}
          onLoadSuccess={onDocumentLoadSuccess}
          loading={<Skeleton className="w-full h-full" />}
        >
          <div className="flex flex-col items-center">
            <div className="flex items-center gap-4 mb-4">
              <button
                onClick={() => setPageNumber((prev) => Math.max(prev - 1, 1))}
                disabled={pageNumber <= 1}
                className="px-4 py-2 bg-gray-100 rounded hover:bg-gray-200 disabled:opacity-50"
              >
                이전
              </button>
              <span>
                페이지 {pageNumber} / {numPages}
              </span>
              <button
                onClick={() => setPageNumber((prev) => Math.min(prev + 1, numPages))}
                disabled={pageNumber >= numPages}
                className="px-4 py-2 bg-gray-100 rounded hover:bg-gray-200 disabled:opacity-50"
              >
                다음
              </button>
            </div>
            <Page
              pageNumber={pageNumber}
              width={800}
              renderTextLayer={true}
              renderAnnotationLayer={true}
            >
              {/* 하이라이트 렌더링 */}
              {highlights
                .filter((h) => h.page === pageNumber)
                .map((highlight, index) => (
                  <div
                    key={index}
                    className="absolute bg-yellow-200 opacity-50"
                    style={{
                      left: `${highlight.position.x}px`,
                      top: `${highlight.position.y}px`,
                      width: `${highlight.width}px`,
                      height: `${highlight.height}px`,
                    }}
                  />
                ))}
            </Page>
          </div>
        </Document>
      </div>
    </div>
  )
}
